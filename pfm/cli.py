"""Command line interface (roadmap V1 to V10).

Design rules:

* every subcommand is a small function ``cmd_*(args, config) -> int`` so it can
  be tested directly;
* ``--config``/``--portfolio-root`` are accepted both before and after the
  subcommand;
* the interactive menu is what you get when running ``pfm`` with no argument;
* expected failures (bad metadata, missing file) print one readable message and
  return 1 — never a traceback.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .check import format_report, run_checks
from .config import Config, load_config
from .create import Draft, create_entry
from .errors import EntryError, PortfolioError, ValidationError
from .hugo import hugo_checks, normalize_portfolio
from .index import generate_indexes
from .models import CONTENT_TYPES, FIELD_LABELS, STATUSES, type_fields
from .naming import parse_tags
from .prompts import prompt_new_entry, prompt_status, run_menu
from .stats import collect_stats, format_stats, write_stats_json
from .store import iter_entries, resolve_entry_id
from .update import update_entry

EXIT_OK = 0
EXIT_ERROR = 1

#: Command name -> canonical command (argparse keeps the alias the user typed).
ALIASES: dict[str, str] = {
    "n": "new",
    "add": "new",
    "create": "new",
    "ls": "list",
    "l": "list",
    "cat": "show",
    "u": "update",
    "c": "check",
    "lint": "check",
    "st": "stats",
    "i": "index",
    "idx": "index",
    "web": "serve",
    "ui": "serve",
}

EXAMPLES = """\
examples:
  pfm new project                    # guided creation
  pfm new publication -T "OSINT notes" -d society -s political-science --no-input
  pfm list --status published
  pfm update content/.../entry.md --status published
  pfm update-status content/.../entry.md published
  pfm check --strict
  pfm stats --write
  pfm index --hugo-links
  pfm serve                          # local web UI on http://127.0.0.1:8765
"""


def _out(args: argparse.Namespace, message: str = "") -> None:
    """Print unless ``--quiet`` was requested."""
    if not getattr(args, "quiet", False):
        print(message)


def _common_options() -> argparse.ArgumentParser:
    """Options accepted by every subcommand (kept after the command name)."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-c",
        "--config",
        metavar="PATH",
        default=argparse.SUPPRESS,
        help="path to config.json",
    )
    common.add_argument(
        "-r",
        "--portfolio-root",
        metavar="PATH",
        default=argparse.SUPPRESS,
        help="override the portfolio root",
    )
    common.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=argparse.SUPPRESS,
        help="only print errors",
    )
    return common


def _add_type_metadata_options(parser: argparse.ArgumentParser) -> None:
    """Add one option per type-specific metadata field."""
    for field, label in FIELD_LABELS.items():
        parser.add_argument(f"--{field.replace('_', '-')}", dest=field, metavar="VALUE", help=label)


def build_parser() -> argparse.ArgumentParser:
    """Build the full argument parser."""
    common = _common_options()
    parser = argparse.ArgumentParser(
        prog="pfm",
        description=("Portfolio Manager - create, update, check and publish a Markdown portfolio."),
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-c", "--config", metavar="PATH", help="path to config.json")
    parser.add_argument(
        "-r", "--portfolio-root", metavar="PATH", help="override the portfolio root"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="only print errors")
    parser.add_argument(
        "-V", "--version", action="version", version=f"portfolio-manager {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    init_parser = subparsers.add_parser(
        "init",
        aliases=["bootstrap"],
        parents=[common],
        help="create a portfolio skeleton and a config.json",
    )
    init_parser.add_argument("path", nargs="?", default=".", help="portfolio root (default: .)")
    init_parser.add_argument("--force", action="store_true", help="overwrite config.json")

    new_parser = subparsers.add_parser(
        "new",
        aliases=["n", "add", "create"],
        parents=[common],
        help="create a new entry",
    )
    new_parser.add_argument("content_type", nargs="?", choices=CONTENT_TYPES)
    new_parser.add_argument("-t", "--type", dest="type_flag", choices=CONTENT_TYPES)
    new_parser.add_argument("-T", "--title", help="entry title")
    new_parser.add_argument("-d", "--domain", help="portfolio domain")
    new_parser.add_argument("-s", "--subdomain", help="portfolio subdomain")
    new_parser.add_argument("--tags", help="comma separated tags")
    new_parser.add_argument("--date", help="YYYY, YYYY-MM or YYYY-MM-DD (default: today)")
    new_parser.add_argument("-S", "--status", choices=STATUSES, help="default: draft")
    _add_type_metadata_options(new_parser)
    new_parser.add_argument(
        "--bundle", action="store_true", help="create a Hugo page bundle (slug/index.md)"
    )
    new_parser.add_argument(
        "--body-file",
        metavar="PATH",
        help="Markdown body instead of the template ('-' reads stdin)",
    )
    new_parser.add_argument("--overwrite", action="store_true", help="replace an existing entry")
    new_parser.add_argument("--no-input", action="store_true", help="never prompt (scripting mode)")

    list_parser = subparsers.add_parser(
        "list", aliases=["ls", "l"], parents=[common], help="list entries"
    )
    list_parser.add_argument("--type", choices=CONTENT_TYPES)
    list_parser.add_argument("--status", choices=STATUSES)
    list_parser.add_argument("--domain")
    list_parser.add_argument("--tag")
    list_parser.add_argument("--json", action="store_true", help="machine readable output")

    show_parser = subparsers.add_parser(
        "show", aliases=["cat"], parents=[common], help="print an entry"
    )
    show_parser.add_argument("entry", help="entry id (path relative to the portfolio root)")

    update_parser = subparsers.add_parser(
        "update", aliases=["u"], parents=[common], help="update front matter of an entry"
    )
    update_parser.add_argument("entry", help="entry id (path relative to the portfolio root)")
    update_parser.add_argument("-S", "--status", choices=STATUSES)
    update_parser.add_argument("-T", "--title")
    update_parser.add_argument("--date")
    update_parser.add_argument("--tags", help="replace the tag list")
    update_parser.add_argument("--add-tag", action="append", metavar="TAG")
    update_parser.add_argument("--remove-tag", action="append", metavar="TAG")
    _add_type_metadata_options(update_parser)
    update_parser.add_argument(
        "--remove-field",
        action="append",
        choices=[field for fields in map(type_fields, CONTENT_TYPES) for field in fields],
        metavar="FIELD",
        help="remove a type-specific metadata field",
    )
    update_parser.add_argument("--dry-run", action="store_true", help="show changes only")

    status_parser = subparsers.add_parser(
        "update-status",
        parents=[common],
        help="shortcut for 'update --status'",
    )
    status_parser.add_argument("entry", help="entry id")
    status_parser.add_argument("status", choices=STATUSES)

    check_parser = subparsers.add_parser(
        "check", aliases=["c", "lint"], parents=[common], help="validate the portfolio"
    )
    check_parser.add_argument("--json", action="store_true")
    check_parser.add_argument("--strict", action="store_true", help="warnings also fail the check")

    stats_parser = subparsers.add_parser(
        "stats", aliases=["st"], parents=[common], help="portfolio statistics"
    )
    stats_parser.add_argument("--json", action="store_true", help="print JSON")
    stats_parser.add_argument(
        "--write", action="store_true", help="write data/portfolio_stats.json"
    )
    stats_parser.add_argument("--output", metavar="PATH", help="write the JSON to a specific path")

    index_parser = subparsers.add_parser(
        "index", aliases=["i", "idx"], parents=[common], help="generate _index.md pages"
    )
    index_parser.add_argument(
        "--no-drafts", action="store_true", help="leave drafts out of the indexes"
    )
    index_parser.add_argument(
        "--hugo-links", action="store_true", help="use absolute Hugo pretty URLs"
    )
    index_parser.add_argument("--dry-run", action="store_true")

    hugo_parser = subparsers.add_parser(
        "hugo", parents=[common], help="check or normalise front matter for Hugo"
    )
    hugo_parser.add_argument(
        "--apply", action="store_true", help="write the normalised front matter"
    )
    hugo_parser.add_argument("--json", action="store_true")

    serve_parser = subparsers.add_parser(
        "serve", aliases=["web", "ui"], parents=[common], help="run the local web UI"
    )
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--open", action="store_true", help="open the browser")
    serve_parser.add_argument("--verbose", action="store_true", help="log every HTTP request")

    subparsers.add_parser("menu", parents=[common], help="interactive menu (default)")

    return parser


def cmd_init(args: argparse.Namespace) -> int:
    """Create a portfolio skeleton plus a configuration file."""
    root = Path(args.path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "content").mkdir(exist_ok=True)
    (root / "data").mkdir(exist_ok=True)

    config_path = Path(getattr(args, "config", None) or "config.json").expanduser()
    if config_path.exists() and not args.force:
        print(f"config already exists, left untouched: {config_path}", file=sys.stderr)
        return EXIT_ERROR

    try:
        # A relative root keeps config.json valid when the portfolio is moved or
        # copied, which is the normal life of a demo or a template.
        relative_root = os.path.relpath(root, config_path.parent.resolve())
    except ValueError:  # pragma: no cover - different drives on Windows
        relative_root = str(root)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({"portfolio_root": Path(relative_root).as_posix()}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"portfolio created: {root}")
    print(f"configuration written: {config_path}")
    print("next: pfm new project")
    return EXIT_OK


def _draft_from_args(args: argparse.Namespace, content_type: str) -> Draft:
    """Build a :class:`Draft` from command line flags."""
    extras: dict[str, Any] = {}
    for field in type_fields(content_type):
        value = getattr(args, field, None)
        if value:
            extras[field] = value

    body: str | None = None
    if args.body_file:
        if args.body_file == "-":
            body = sys.stdin.read()
        else:
            try:
                body = Path(args.body_file).expanduser().read_text(encoding="utf-8")
            except OSError as exc:
                raise EntryError(f"cannot read body file {args.body_file}: {exc}") from exc

    return Draft(
        content_type=content_type,
        title=args.title or "",
        domain=args.domain or "",
        subdomain=args.subdomain or "",
        tags=parse_tags(args.tags) if args.tags else [],
        date=args.date or "",
        status=args.status or "draft",
        extras=extras,
        bundle=args.bundle,
        body=body,
    )


def cmd_new(args: argparse.Namespace, config: Config) -> int:
    """Create an entry, interactively or from flags."""
    content_type = args.type_flag or args.content_type
    # Prompt only when a human could answer: an explicit --title means the call
    # is scripted, and a pipe or a cron job has no TTY to read from.
    interactive = not args.no_input and args.title is None and sys.stdin.isatty()

    if interactive:
        draft = prompt_new_entry(config, content_type=content_type)
    else:
        if not content_type:
            raise ValidationError(
                "a content type is required",
                [f"allowed types: {', '.join(CONTENT_TYPES)}", "example: pfm new project"],
            )
        if not args.title:
            raise ValidationError(
                "a title is required in non-interactive mode",
                ["use --title or run 'pfm new' without arguments to be guided"],
            )
        draft = _draft_from_args(args, content_type)

    entry = create_entry(config, draft, overwrite=args.overwrite)
    _out(args, f"Created {entry.entry_id}")
    _out(args, f"  {entry.path}")
    return EXIT_OK


def cmd_list(args: argparse.Namespace, config: Config) -> int:
    """List entries with optional filters."""
    entries = iter_entries(config.portfolio_root)
    if args.type:
        entries = [entry for entry in entries if entry.type == args.type]
    if args.status:
        entries = [entry for entry in entries if entry.status == args.status]
    if args.domain:
        entries = [entry for entry in entries if entry.domain == args.domain]
    if args.tag:
        entries = [entry for entry in entries if args.tag in entry.tags]

    if args.json:
        print(json.dumps([entry.to_dict() for entry in entries], indent=2, ensure_ascii=False))
        return EXIT_OK

    if not entries:
        _out(args, "No entry matches.")
        return EXIT_OK

    rows = [
        (entry.status or "-", entry.type or "-", f"{entry.domain}/{entry.subdomain}", entry.title)
        for entry in entries
    ]
    widths = [max(len(row[index]) for row in rows) for index in range(3)]
    for entry, row in zip(entries, rows, strict=False):
        line = "  ".join(row[index].ljust(widths[index]) for index in range(3)) + f"  {row[3]}"
        _out(args, f"{line}\n{'':{sum(widths) + 6}}id: {entry.entry_id}")
    _out(args, f"\n{len(entries)} entry(ies).")
    return EXIT_OK


def cmd_show(args: argparse.Namespace, config: Config) -> int:
    """Print the raw Markdown of an entry."""
    path = resolve_entry_id(config.portfolio_root, args.entry)
    print(path.read_text(encoding="utf-8"), end="")
    return EXIT_OK


def cmd_update(args: argparse.Namespace, config: Config) -> int:
    """Update selected front matter fields."""
    path = resolve_entry_id(config.portfolio_root, args.entry)

    fields: dict[str, str | None] = {}
    for field in FIELD_LABELS:
        value = getattr(args, field, None)
        if value is not None:
            fields[field] = value
    for field in args.remove_field or []:
        fields[field] = None

    result = update_entry(
        config,
        path,
        status=args.status,
        title=args.title,
        date=args.date,
        tags=parse_tags(args.tags) if args.tags is not None else None,
        add_tags=args.add_tag,
        remove_tags=args.remove_tag,
        fields=fields or None,
        dry_run=args.dry_run,
    )

    if not result.changed:
        _out(args, "Nothing to update.")
        return EXIT_OK

    verb = "Would update" if args.dry_run else "Updated"
    _out(args, f"{verb} {result.entry.entry_id}")
    for field, (old, new) in result.changes.items():
        _out(args, f"  {field}: {old!r} -> {new!r}")
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return EXIT_OK


def cmd_update_status(args: argparse.Namespace, config: Config) -> int:
    """Shortcut: change only the status of an entry."""
    path = resolve_entry_id(config.portfolio_root, args.entry)
    result = update_entry(config, path, status=args.status)
    if not result.changed:
        _out(args, f"{result.entry.entry_id} is already {args.status}")
    else:
        _out(args, f"{result.entry.entry_id}: status -> {args.status}")
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return EXIT_OK


def cmd_check(args: argparse.Namespace, config: Config) -> int:
    """Validate the portfolio and set the exit code accordingly."""
    report = run_checks(config)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_report(report, root=config.portfolio_root))
    return EXIT_OK if report.ok(strict=args.strict) else EXIT_ERROR


def cmd_stats(args: argparse.Namespace, config: Config) -> int:
    """Compute and optionally persist statistics."""
    stats = collect_stats(config)
    if args.output:
        destination = write_stats_json(config, stats, Path(args.output).expanduser())
        _out(args, f"Statistics written to {destination}")
    elif args.write:
        destination = write_stats_json(config, stats)
        _out(args, f"Statistics written to {destination}")

    if args.json:
        print(json.dumps(stats.to_dict(), indent=2, ensure_ascii=False))
    elif not args.quiet:
        print(format_stats(stats))
    return EXIT_OK


def cmd_index(args: argparse.Namespace, config: Config) -> int:
    """Regenerate every index page."""
    files = generate_indexes(
        config,
        include_drafts=not args.no_drafts,
        link_style="hugo" if args.hugo_links else "relative",
        dry_run=args.dry_run,
    )
    verb = "Would write" if args.dry_run else "Wrote"
    for path in files:
        try:
            display = path.relative_to(config.portfolio_root)
        except ValueError:  # pragma: no cover - defensive
            display = path
        _out(args, f"{verb} {display}")
    _out(args, f"{len(files)} index page(s).")
    return EXIT_OK


def cmd_hugo(args: argparse.Namespace, config: Config) -> int:
    """Normalise front matter for Hugo and/or report Hugo-specific problems."""
    if args.apply:
        changed = normalize_portfolio(config)
        if changed:
            _out(args, f"Normalised {len(changed)} entry(ies).")
        else:
            _out(args, "Nothing to normalise.")

    issues = hugo_checks(config)
    errors = [issue for issue in issues if issue.is_error]
    if args.json:
        print(
            json.dumps(
                {
                    "errors": [issue.to_dict() for issue in errors],
                    "warnings": [issue.to_dict() for issue in issues if not issue.is_error],
                    "ok": not errors,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        for issue in issues:
            marker = "ERROR  " if issue.is_error else "WARNING"
            _out(args, f"{marker} {issue.code} {issue.path}: {issue.message}")
        _out(args, "Hugo check: OK" if not errors else "Hugo check: failed")
    return EXIT_OK if not errors else EXIT_ERROR


def cmd_serve(args: argparse.Namespace, config: Config) -> int:
    """Start the local web interface (imported lazily)."""
    if getattr(args, "verbose", False):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    from .server import serve

    serve(config, host=args.host, port=args.port, open_browser=args.open)
    return EXIT_OK


def cmd_menu(args: argparse.Namespace, config: Config) -> int:
    """Interactive menu: a thin wrapper over the other commands."""

    def menu_new() -> int:
        draft = prompt_new_entry(config)
        entry = create_entry(config, draft)
        print(f"Created {entry.entry_id}")
        return EXIT_OK

    def menu_list() -> int:
        namespace = argparse.Namespace(
            type=None, status=None, domain=None, tag=None, json=False, quiet=False
        )
        return cmd_list(namespace, config)

    def menu_update() -> int:
        entry_id = input("Entry id: ").strip()
        status = prompt_status()
        path = resolve_entry_id(config.portfolio_root, entry_id)
        result = update_entry(config, path, status=status)
        print(f"{result.entry.entry_id}: {dict(result.changes) or 'no change'}")
        return EXIT_OK

    def menu_check() -> int:
        return cmd_check(argparse.Namespace(json=False, strict=False, quiet=False), config)

    def menu_stats() -> int:
        return cmd_stats(
            argparse.Namespace(json=False, write=False, output=None, quiet=False), config
        )

    def menu_index() -> int:
        return cmd_index(
            argparse.Namespace(no_drafts=False, hugo_links=False, dry_run=False, quiet=False),
            config,
        )

    def menu_serve() -> int:
        return cmd_serve(
            argparse.Namespace(host="127.0.0.1", port=8765, open=True, quiet=False), config
        )

    handlers = {
        "new": menu_new,
        "list": menu_list,
        "update": menu_update,
        "check": menu_check,
        "stats": menu_stats,
        "index": menu_index,
        "serve": menu_serve,
        "quit": lambda: EXIT_OK,
    }
    return run_menu(config, handlers)


HANDLERS = {
    "new": cmd_new,
    "list": cmd_list,
    "show": cmd_show,
    "update": cmd_update,
    "update-status": cmd_update_status,
    "check": cmd_check,
    "stats": cmd_stats,
    "index": cmd_index,
    "hugo": cmd_hugo,
    "serve": cmd_serve,
    "menu": cmd_menu,
}


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse arguments, load configuration, dispatch."""
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command
    if command in ALIASES:
        command = ALIASES[command]

    try:
        if command == "init":
            return cmd_init(args)

        config = load_config(
            getattr(args, "config", None),
            portfolio_root=getattr(args, "portfolio_root", None),
        )
        if command is None:
            return cmd_menu(args, config)
        handler = HANDLERS[command]
        return handler(args, config)
    except ValidationError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        for detail in exc.details:
            print(f"  - {detail}", file=sys.stderr)
        return EXIT_ERROR
    except PortfolioError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:  # pragma: no cover - user interruption
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
