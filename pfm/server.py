"""Local web interface (roadmap V10).

Why a local web UI instead of Tkinter: it works on any machine with a browser,
including a headless server or a container, it needs no GUI toolkit and it can
be tested end to end in CI by talking HTTP to a server bound to ``127.0.0.1``.

Security model (deliberately small, the server is a local tool):

* binds to loopback by default;
* refuses requests whose ``Host`` header is not a loopback name (DNS rebinding);
* refuses cross-origin requests (``Origin`` must match ``Host``);
* writes require ``Content-Type: application/json``, which a cross-site HTML
  form cannot produce without a CORS preflight;
* every entry id goes through :func:`pfm.store.resolve_entry_id`, so no request
  can read or write outside the portfolio;
* only the three bundled assets are served statically, never arbitrary files.
"""

from __future__ import annotations

import json
import logging
import threading
import webbrowser
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from . import __version__
from .check import format_report, run_checks
from .config import Config
from .create import Draft, create_entry
from .errors import EntryError, EntryNotFoundError, PortfolioError, UnsafePathError, ValidationError
from .hugo import hugo_checks, normalize_portfolio
from .index import LINK_STYLES, generate_indexes
from .markdown import render_markdown
from .models import CONTENT_TYPES, FIELD_LABELS, STATUSES, TYPE_METADATA_FIELDS
from .naming import parse_tags
from .stats import collect_stats, write_stats_json
from .store import iter_entries, read_entry, resolve_entry_id
from .update import update_entry

LOGGER = logging.getLogger("pfm.server")

#: Directory holding the static assets shipped with the package.
WEB_ROOT = Path(__file__).resolve().parent / "web"

#: Maximum accepted request body (1 MiB is far more than any portfolio entry).
MAX_BODY_BYTES = 1_048_576

#: Static assets exposed by the server.
STATIC_ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/static/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/static/style.css": ("style.css", "text/css; charset=utf-8"),
}

#: Host names accepted in the Host header.
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]"}


class ApiError(PortfolioError):
    """An error that maps to a precise HTTP status."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


class PortfolioRequestHandler(BaseHTTPRequestHandler):
    """Request handler for the Portfolio Manager web UI."""

    server_version = f"PortfolioManager/{__version__}"
    # HTTP/1.0 closes the connection after each response.  For a local tool the
    # cost is irrelevant, and it removes a whole class of keep-alive framing
    # bugs (a desynchronised socket can make the next request look like an
    # unknown method and answer 501).
    protocol_version = "HTTP/1.0"

    @property
    def app(self) -> PortfolioHTTPServer:
        """Typed access to the server instance (config, lock, bind host)."""
        return self.server  # type: ignore[return-value]

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        """Route the access log to the module logger."""
        LOGGER.info("%s - %s", self.address_string(), format % args)

    def _send_bytes(self, payload: bytes, content_type: str, status: int = 200) -> None:
        """Write a response with an explicit length, body omitted for ``HEAD``.

        ``Cache-Control: no-store`` is deliberate: after an edit the browser
        must never show a stale entry.
        """
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _send_json(self, payload: Any, status: int = 200) -> None:
        """Serialise ``payload`` as UTF-8 JSON."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status=status)

    def _send_error_json(
        self, message: str, status: int, *, details: list[str] | None = None
    ) -> None:
        """Send the ``{"error": {...}}`` envelope the web UI reads.

        ``details`` is only present when the failure came from a validator that
        could list one problem per field.
        """
        payload: dict[str, Any] = {"error": {"message": message, "status": int(status)}}
        if details:
            payload["error"]["details"] = details
        self._send_json(payload, status=status)

    def _check_origin(self) -> None:
        """Reject cross-origin requests and DNS rebinding attempts."""
        host = (self.headers.get("Host") or "").strip()
        # An IPv6 literal is bracketed ("[::1]:8765"), so the last colon is the
        # port separator only outside brackets; a bare "[::1]" ends the host.
        hostname = host.rsplit(":", 1)[0] if host and not host.endswith("]") else host
        if host and hostname not in LOOPBACK_HOSTS and hostname != self.app.bind_host:
            raise ApiError("invalid Host header", HTTPStatus.FORBIDDEN)

        origin = self.headers.get("Origin")
        if origin:
            allowed = {f"http://{host}", f"https://{host}"} if host else set()
            if origin not in allowed:
                raise ApiError("cross-origin request refused", HTTPStatus.FORBIDDEN)

    def _read_json(self) -> dict[str, Any]:
        """Read and validate a JSON request body."""
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type != "application/json":
            raise ApiError(
                "Content-Type must be application/json", HTTPStatus.UNSUPPORTED_MEDIA_TYPE
            )

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError as exc:
            raise ApiError("invalid Content-Length", HTTPStatus.BAD_REQUEST) from exc
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ApiError("request body too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)

        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError("invalid JSON body", HTTPStatus.BAD_REQUEST) from exc
        if not isinstance(payload, dict):
            raise ApiError("the JSON body must be an object", HTTPStatus.BAD_REQUEST)
        return payload

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        """Serve the UI, the API resources and nothing else."""
        self._dispatch("GET")

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib naming
        """Same as GET without a body."""
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        """Create entries, run checks, regenerate indexes."""
        self._dispatch("POST")

    def do_PATCH(self) -> None:  # noqa: N802 - stdlib naming
        """Update metadata of one entry."""
        self._dispatch("PATCH")

    def do_DELETE(self) -> None:  # noqa: N802 - stdlib naming
        """Delete one entry."""
        self._dispatch("DELETE")

    def _dispatch(self, method: str) -> None:
        """Route the request and map expected failures onto HTTP statuses.

        The ``except`` order matters: ``EntryNotFoundError`` and
        ``UnsafePathError`` are ``EntryError`` subclasses, so they have to be
        caught before it or every missing entry would become a 409.
        """
        try:
            self._check_origin()
            route = self._route(method)
            route()
        except ValidationError as exc:
            self._send_error_json(exc.message, HTTPStatus.BAD_REQUEST, details=exc.details)
        except ApiError as exc:
            self._send_error_json(str(exc), exc.status)
        except EntryNotFoundError as exc:
            self._send_error_json(str(exc), HTTPStatus.NOT_FOUND)
        except UnsafePathError as exc:
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
        except EntryError as exc:
            self._send_error_json(str(exc), HTTPStatus.CONFLICT)
        except PortfolioError as exc:  # pragma: no cover - defensive
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
        except Exception:  # pragma: no cover - unexpected bug
            LOGGER.exception("unhandled error while serving %s %s", method, self.path)
            self._send_error_json("internal server error", HTTPStatus.INTERNAL_SERVER_ERROR)

    def _route(self, method: str) -> Callable[[], None]:
        """Return the callable handling ``method`` and the current path."""
        split = urlsplit(self.path)
        path = unquote(split.path)
        query = parse_qs(split.query)

        if method == "GET":
            if path in STATIC_ASSETS:
                asset, content_type = STATIC_ASSETS[path]
                return lambda: self._send_bytes((WEB_ROOT / asset).read_bytes(), content_type)
            if path == "/api/meta":
                return self._api_meta
            if path == "/api/entries":
                return lambda: self._api_entries(query)
            if path.startswith("/api/entries/"):
                entry_id = path[len("/api/entries/") :]
                return lambda: self._api_entry_detail(entry_id)
            if path == "/api/stats":
                return self._api_stats
            if path == "/api/health":
                return lambda: self._send_json({"status": "ok", "version": __version__})

        if method == "POST":
            if path == "/api/entries":
                return self._api_create
            if path == "/api/check":
                return self._api_check
            if path == "/api/index":
                return self._api_index
            if path == "/api/stats":
                return self._api_write_stats
            if path == "/api/hugo":
                return self._api_hugo

        if method == "PATCH" and path.startswith("/api/entries/"):
            entry_id = path[len("/api/entries/") :]
            return lambda: self._api_update(entry_id)

        if method == "DELETE" and path.startswith("/api/entries/"):
            entry_id = path[len("/api/entries/") :]
            return lambda: self._api_delete(entry_id)

        raise ApiError(f"no route for {method} {path}", HTTPStatus.NOT_FOUND)

    def _api_meta(self) -> None:
        """Describe the vocabulary the UI needs to build its forms.

        Types with their metadata fields, human labels, statuses, domains and
        default tags, in one round trip.
        """
        config = self.app.config
        self._send_json(
            {
                "version": __version__,
                "portfolio_root": str(config.portfolio_root),
                "types": [
                    {
                        "value": content_type,
                        "fields": list(TYPE_METADATA_FIELDS.get(content_type, ())),
                    }
                    for content_type in CONTENT_TYPES
                ],
                "field_labels": FIELD_LABELS,
                "statuses": list(STATUSES),
                "domains": {key: list(value) for key, value in config.domains.items()},
                "default_tags": list(config.default_tags),
            }
        )

    def _api_entries(self, query: dict[str, list[str]]) -> None:
        """List entries as summaries, filtered by the query string.

        Filtering runs in memory: a portfolio holds a few hundred files at
        most, so an index would buy nothing and could only drift.
        """
        entries = iter_entries(self.app.config.portfolio_root)

        def first(name: str) -> str | None:
            values = query.get(name)
            return values[0] if values else None

        content_type = first("type")
        status = first("status")
        domain = first("domain")
        tag = first("tag")
        search = (first("q") or "").lower()

        if content_type:
            entries = [entry for entry in entries if entry.type == content_type]
        if status:
            entries = [entry for entry in entries if entry.status == status]
        if domain:
            entries = [entry for entry in entries if entry.domain == domain]
        if tag:
            entries = [entry for entry in entries if tag in entry.tags]
        if search:
            entries = [
                entry
                for entry in entries
                if search in entry.title.lower()
                or search in entry.entry_id.lower()
                or any(search in item for item in entry.tags)
            ]

        self._send_json({"count": len(entries), "entries": [entry.to_dict() for entry in entries]})

    def _api_entry_detail(self, entry_id: str) -> None:
        """Return one entry: summary, raw Markdown and rendered HTML.

        The raw text is read again instead of rebuilt from the parsed entry, so
        the preview shows the file exactly as it is on disk, hand edits
        included.
        """
        path = resolve_entry_id(self.app.config.portfolio_root, entry_id)
        entry = read_entry(path, self.app.config.portfolio_root)
        text = path.read_text(encoding="utf-8")
        self._send_json(
            {
                "entry": entry.to_dict(),
                "markdown": text,
                "html": render_markdown(entry.body),
                "raw_body": entry.body,
            }
        )

    def _api_create(self) -> None:
        """Create one entry from the JSON body and answer 201.

        ``type`` and ``content_type`` are accepted as synonyms so a client that
        uses the data-model name works as well as the UI, which posts ``type``.
        """
        payload = self._read_json()
        content_type = str(payload.get("type") or payload.get("content_type") or "")
        extras_payload = payload.get("fields") or {}
        if not isinstance(extras_payload, dict):
            raise ApiError("'fields' must be an object")

        tags_value = payload.get("tags", [])
        tags = parse_tags(tags_value) if isinstance(tags_value, (str, list)) else []

        draft = Draft(
            content_type=content_type,
            title=str(payload.get("title") or ""),
            domain=str(payload.get("domain") or ""),
            subdomain=str(payload.get("subdomain") or ""),
            tags=tags,
            date=str(payload.get("date") or ""),
            status=str(payload.get("status") or "draft"),
            extras={str(key): str(value) for key, value in extras_payload.items() if value},
            bundle=bool(payload.get("bundle", False)),
            body=str(payload["body"]) if payload.get("body") else None,
        )
        with self.app.lock:
            entry = create_entry(self.app.config, draft, overwrite=bool(payload.get("overwrite")))
        self._send_json({"entry": entry.to_dict()}, status=HTTPStatus.CREATED)

    def _api_update(self, entry_id: str) -> None:
        """Apply a partial front matter update and report what changed.

        Omitted keys are left untouched, a ``fields`` entry set to null removes
        the field, and the response lists each change so the UI can show a
        before/after without a second read.
        """
        payload = self._read_json()
        path = resolve_entry_id(self.app.config.portfolio_root, entry_id)

        fields_payload = payload.get("fields") or {}
        if not isinstance(fields_payload, dict):
            raise ApiError("'fields' must be an object")
        fields = {
            str(key): (None if value is None else str(value))
            for key, value in fields_payload.items()
        }

        tags_value = payload.get("tags")
        tags = parse_tags(tags_value) if isinstance(tags_value, (str, list)) else None
        add_tags = (
            parse_tags(payload["add_tags"])
            if isinstance(payload.get("add_tags"), (str, list))
            else None
        )
        remove_tags = (
            parse_tags(payload["remove_tags"])
            if isinstance(payload.get("remove_tags"), (str, list))
            else None
        )

        with self.app.lock:
            result = update_entry(
                self.app.config,
                path,
                status=payload.get("status"),
                title=payload.get("title"),
                date=payload.get("date"),
                tags=tags,
                add_tags=add_tags,
                remove_tags=remove_tags,
                fields=fields or None,
            )
        self._send_json(
            {
                "entry": result.entry.to_dict(),
                "changes": {key: list(value) for key, value in result.changes.items()},
                "warnings": result.warnings,
            }
        )

    def _api_delete(self, entry_id: str) -> None:
        """Delete one entry and answer 204 without a body."""
        path = resolve_entry_id(self.app.config.portfolio_root, entry_id)
        with self.app.lock:
            path.unlink()
        # Built by hand rather than through _send_json: 204 means no content,
        # and the UI only looks at the status code here.
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _api_stats(self) -> None:
        """Compute the statistics without writing anything to disk."""
        self._send_json(collect_stats(self.app.config).to_dict())

    def _api_write_stats(self) -> None:
        """Compute the statistics and persist them to ``data/``."""
        destination = write_stats_json(self.app.config, collect_stats(self.app.config))
        self._send_json({"written": str(destination)})

    def _api_check(self) -> None:
        """Run the checks and return the JSON report plus its text rendering."""
        report = run_checks(self.app.config)
        payload = report.to_dict()
        payload["text"] = format_report(report)
        self._send_json(payload)

    def _api_hugo(self) -> None:
        """Normalise front matter on demand and report Hugo readiness."""
        payload = self._read_json()
        changed: list[str] = []
        if payload.get("apply"):
            with self.app.lock:
                changed = normalize_portfolio(self.app.config)
        issues = hugo_checks(self.app.config)
        errors = [issue.to_dict() for issue in issues if issue.is_error]
        self._send_json(
            {
                "changed": changed,
                "errors": errors,
                "warnings": [issue.to_dict() for issue in issues if not issue.is_error],
                "ok": not errors,
            }
        )

    def _api_index(self) -> None:
        """Regenerate the index pages; ``dry_run`` reports without writing."""
        payload = self._read_json()
        link_style = str(payload.get("link_style", "relative"))
        if link_style not in LINK_STYLES:
            raise ApiError(f"unknown link style: {link_style}")
        files = generate_indexes(
            self.app.config,
            include_drafts=bool(payload.get("include_drafts", True)),
            link_style=link_style,
            dry_run=bool(payload.get("dry_run", False)),
        )
        root = self.app.config.portfolio_root
        self._send_json({"files": [path.relative_to(root).as_posix() for path in files]})


class PortfolioHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying the configuration and a write lock."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], config: Config, bind_host: str) -> None:
        """Bind the handler to a configuration and create the write lock.

        One lock is enough: writes are short and all of them mutate the same
        tree, so serialising them costs nothing at this scale.
        """
        super().__init__(address, PortfolioRequestHandler)
        self.config = config
        self.bind_host = bind_host
        self.lock = threading.Lock()


def create_server(config: Config, host: str = "127.0.0.1", port: int = 8765) -> PortfolioHTTPServer:
    """Create (but do not start) the web server.

    Args:
        config: Resolved configuration.
        host: Interface to bind; keep the loopback default.
        port: TCP port; ``0`` picks a free port (used by the tests).
    """
    if not WEB_ROOT.is_dir():
        raise EntryError(f"web assets are missing: {WEB_ROOT}")
    server = PortfolioHTTPServer((host, port), config, bind_host=host)
    return server


def serve(
    config: Config,
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    open_browser: bool = False,
) -> None:
    """Run the web UI until interrupted.

    Binding outside loopback is possible but warns loudly: the API has no
    authentication, so reachability equals write access to the portfolio.
    """
    if host not in LOOPBACK_HOSTS:
        print(
            f"warning: the web UI is bound to {host}, not loopback. "
            "Anyone who can reach this port can edit the portfolio.",
        )

    server = create_server(config, host, port)
    actual_port = server.server_address[1]
    # A wildcard bind cannot be typed into a browser, so the printed URL stays
    # on loopback even when the server listens on every interface.
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{display_host}:{actual_port}/"

    print(f"Portfolio Manager web UI: {url}")
    print(f"Portfolio: {config.portfolio_root}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        server.server_close()
