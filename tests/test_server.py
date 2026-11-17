"""End-to-end tests for the local web UI and its JSON API.

The server is started on an ephemeral port bound to ``127.0.0.1`` and driven
over real HTTP, which is as close to the browser behaviour as CI can get.
"""

from __future__ import annotations

import json
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from pfm.create import Draft, create_entry
from pfm.server import create_server
from tests.helpers import make_config


class ServerTestCase(unittest.TestCase):
    """Start one server per test class, with a fresh portfolio per test."""

    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name) / "portfolio"
        (self.root / "content").mkdir(parents=True)
        self.config = make_config(self.root)
        self.server = create_server(self.config, "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def request(
        self,
        method: str,
        path: str,
        payload: object | None = None,
        *,
        content_type: str = "application/json",
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any]:
        """Send a request and return ``(status, parsed JSON or text)``."""
        connection = HTTPConnection("127.0.0.1", self.port, timeout=5)
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request_headers = {"Host": f"127.0.0.1:{self.port}"}
        if payload is not None:
            request_headers["Content-Type"] = content_type
        request_headers.update(headers or {})
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            raw = response.read()
            status = response.status
            media = response.getheader("Content-Type") or ""
        finally:
            connection.close()

        if "application/json" in media:
            return status, json.loads(raw.decode("utf-8"))
        return status, raw.decode("utf-8", errors="replace")

    def make_entry(self, title: str = "Server entry") -> str:
        entry = create_entry(
            self.config,
            Draft(
                content_type="project",
                title=title,
                domain="technology",
                subdomain="computer-science",
                tags=["python"],
                status="draft",
            ),
        )
        return entry.entry_id


class StaticTests(ServerTestCase):
    def test_index_page(self) -> None:
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Portfolio Manager", body)
        self.assertIn("/static/app.js", body)

    def test_static_assets(self) -> None:
        status, body = self.request("GET", "/static/app.js")
        self.assertEqual(status, 200)
        self.assertIn("loadEntries", body)
        status, body = self.request("GET", "/static/style.css")
        self.assertEqual(status, 200)
        self.assertIn("--accent", body)

    def test_health(self) -> None:
        status, payload = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_unknown_route(self) -> None:
        status, payload = self.request("GET", "/etc/passwd")
        self.assertEqual(status, 404)

    def test_head_request_has_no_body(self) -> None:
        status, body = self.request("HEAD", "/")
        self.assertEqual(status, 200)
        self.assertEqual(body, "")


class MetaTests(ServerTestCase):
    def test_meta(self) -> None:
        status, payload = self.request("GET", "/api/meta")
        self.assertEqual(status, 200)
        self.assertIn("technology", payload["domains"])
        self.assertEqual(payload["statuses"], ["draft", "in-progress", "published"])
        fields = {item["value"]: item["fields"] for item in payload["types"]}
        self.assertEqual(fields["project"], ["repository", "demo"])


class EntryApiTests(ServerTestCase):
    def test_create_list_detail(self) -> None:
        status, payload = self.request(
            "POST",
            "/api/entries",
            {
                "type": "publication",
                "title": "Web created",
                "domain": "society",
                "subdomain": "political-science",
                "tags": "osint, sahel",
                "date": "2026-05-01",
                "status": "published",
                "fields": {"pdf": "https://example.org/p.pdf"},
            },
        )
        self.assertEqual(status, 201, payload)
        entry_id = payload["entry"]["id"]
        self.assertIn("web-created.md", entry_id)
        self.assertTrue((self.root / entry_id).is_file())

        status, listing = self.request("GET", "/api/entries")
        self.assertEqual(status, 200)
        self.assertEqual(listing["count"], 1)
        self.assertEqual(listing["entries"][0]["title"], "Web created")

        status, detail = self.request("GET", f"/api/entries/{entry_id}")
        self.assertEqual(status, 200)
        self.assertIn("<h1>Web created</h1>", detail["html"])
        self.assertIn("status: published", detail["markdown"])

    def test_create_validation_error(self) -> None:
        status, payload = self.request(
            "POST",
            "/api/entries",
            {
                "type": "project",
                "title": "",
                "domain": "technology",
                "subdomain": "computer-science",
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("message", payload["error"])
        self.assertIn("title", payload["error"]["message"])

    def test_create_duplicate_is_a_conflict(self) -> None:
        self.make_entry()
        status, payload = self.request(
            "POST",
            "/api/entries",
            {
                "type": "project",
                "title": "Server entry",
                "domain": "technology",
                "subdomain": "computer-science",
            },
        )
        self.assertEqual(status, 409)
        self.assertIn("overwrite", payload["error"]["message"])

    def test_filters(self) -> None:
        self.make_entry("One")
        self.make_entry("Two")
        status, payload = self.request("GET", "/api/entries?q=two")
        self.assertEqual(payload["count"], 1)
        status, payload = self.request("GET", "/api/entries?status=published")
        self.assertEqual(payload["count"], 0)

    def test_update_status(self) -> None:
        entry_id = self.make_entry()
        status, payload = self.request("PATCH", f"/api/entries/{entry_id}", {"status": "published"})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["entry"]["status"], "published")
        self.assertFalse(payload["entry"]["draft"])
        self.assertIn("status", payload["changes"])

        text = (self.root / entry_id).read_text(encoding="utf-8")
        self.assertIn("draft: false", text)

    def test_update_fields_and_tags(self) -> None:
        entry_id = self.make_entry()
        status, payload = self.request(
            "PATCH",
            f"/api/entries/{entry_id}",
            {
                "tags": "a, b",
                "add_tags": "c",
                "fields": {"repository": "https://example.org/repo"},
            },
        )
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["entry"]["tags"], ["a", "b", "c"])
        self.assertEqual(payload["entry"]["metadata"]["repository"], "https://example.org/repo")

    def test_update_invalid_field(self) -> None:
        entry_id = self.make_entry()
        status, payload = self.request(
            "PATCH", f"/api/entries/{entry_id}", {"fields": {"pdf": "x.pdf"}}
        )
        self.assertEqual(status, 400)
        self.assertIn("not a metadata field", payload["error"]["message"])

    def test_update_missing_entry(self) -> None:
        status, _ = self.request(
            "PATCH", "/api/entries/content/missing.md", {"status": "published"}
        )
        self.assertEqual(status, 404)

    def test_delete(self) -> None:
        entry_id = self.make_entry()
        status, _ = self.request("DELETE", f"/api/entries/{entry_id}")
        self.assertEqual(status, 204)
        self.assertFalse((self.root / entry_id).exists())

    def test_path_traversal_is_refused(self) -> None:
        for path in (
            "/api/entries/../../etc/passwd",
            "/api/entries/%2e%2e/%2e%2e/etc/passwd",
            "/api/entries//etc/passwd",
        ):
            with self.subTest(path=path):
                status, payload = self.request("GET", path)
                self.assertIn(status, (400, 404))

    def test_invalid_json_body(self) -> None:
        status, payload = self.request("POST", "/api/entries", None)
        self.assertIn(status, (400, 415))

    def test_wrong_content_type_is_refused(self) -> None:
        status, payload = self.request(
            "POST",
            "/api/entries",
            {"type": "project"},
            content_type="text/plain",
        )
        self.assertEqual(status, 415)

    def test_cross_origin_is_refused(self) -> None:
        status, payload = self.request(
            "GET", "/api/entries", headers={"Origin": "http://evil.example"}
        )
        self.assertEqual(status, 403)

    def test_matching_origin_is_allowed(self) -> None:
        status, _ = self.request(
            "GET",
            "/api/entries",
            headers={"Origin": f"http://127.0.0.1:{self.port}"},
        )
        self.assertEqual(status, 200)

    def test_dns_rebinding_host_is_refused(self) -> None:
        status, payload = self.request("GET", "/api/entries", headers={"Host": "evil.example:80"})
        self.assertEqual(status, 403)


class ToolApiTests(ServerTestCase):
    def test_stats(self) -> None:
        self.make_entry()
        status, payload = self.request("GET", "/api/stats")
        self.assertEqual(status, 200)
        self.assertEqual(payload["total"], 1)
        self.assertIn("by_status", payload)

    def test_write_stats(self) -> None:
        self.make_entry()
        status, payload = self.request("POST", "/api/stats", {})
        self.assertEqual(status, 200)
        self.assertTrue(Path(payload["written"]).is_file())

    def test_check(self) -> None:
        self.make_entry()
        status, payload = self.request("POST", "/api/check", {})
        self.assertEqual(status, 200)
        self.assertEqual(payload["checked"], 1)
        self.assertIn("text", payload)

    def test_index(self) -> None:
        self.make_entry()
        status, payload = self.request(
            "POST", "/api/index", {"link_style": "hugo", "include_drafts": False}
        )
        self.assertEqual(status, 200, payload)
        self.assertIn("content/_index.md", payload["files"])

    def test_index_rejects_unknown_style(self) -> None:
        status, payload = self.request("POST", "/api/index", {"link_style": "weird"})
        self.assertEqual(status, 400)

    def test_hugo(self) -> None:
        self.make_entry()
        status, payload = self.request("POST", "/api/hugo", {"apply": True})
        self.assertEqual(status, 200, payload)
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
