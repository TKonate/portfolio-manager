#!/usr/bin/env python3
"""Regenerate the demonstration portfolio shipped in ``examples/portfolio``.

The script is deliberately idempotent: entries that already exist are left
untouched, so it can be run again after a checkout or a merge.

Usage::

    python examples/build_demo.py

It also demonstrates the page-bundle feature: the PDF stored in
``examples/portfolio/assets`` is copied next to the publication's ``index.md``.
"""

from __future__ import annotations

from pathlib import Path

from pfm.config import load_config
from pfm.create import Draft, create_entry
from pfm.errors import EntryError

ROOT = Path(__file__).resolve().parent
PDF = ROOT / "portfolio" / "assets" / "demo-publication.pdf"

ENTRIES: tuple[Draft, ...] = (
    Draft(
        content_type="project",
        title="Portfolio Manager",
        domain="technology",
        subdomain="computer-science",
        tags=["python", "cli", "markdown"],
        status="published",
        date="2026-11-17",
        extras={
            "repository": "https://github.com/TKonate/portfolio-manager",
            "demo": "https://github.com/TKonate/portfolio-manager#usage",
        },
    ),
    Draft(
        content_type="project",
        title="Homelab sensor node",
        domain="technology",
        subdomain="electronics",
        tags=["esp32", "mqtt", "homelab"],
        status="in-progress",
        date="2026-10-04",
    ),
    Draft(
        content_type="lab",
        title="MailGuard threat model",
        domain="security",
        subdomain="cybersecurity",
        tags=["threat-modeling", "stride", "email"],
        status="published",
        date="2026-09-23",
        extras={"diagram": "https://example.org/diagrams/mailguard-stride.png"},
    ),
    Draft(
        content_type="lab",
        title="OSINT collection pipeline",
        domain="security",
        subdomain="osint",
        tags=["osint", "python", "automation"],
        status="published",
        date="2026-08-12",
        extras={"dataset": "https://example.org/datasets/osint-sample.json"},
    ),
    Draft(
        content_type="publication",
        title="Civilian populations and fragmented sovereignties",
        domain="society",
        subdomain="political-science",
        tags=["political-science", "osint", "sahel"],
        status="published",
        date="2026",
        extras={
            "source_url": "https://example.org/publications/fragmented-sovereignties",
            "pdf": str(PDF),
        },
        bundle=True,
    ),
    Draft(
        content_type="reading",
        title="Thinking in Systems",
        domain="interdisciplinary",
        subdomain="general",
        tags=["systems-thinking", "reading"],
        status="draft",
        date="2026",
        extras={"author": "Donella H. Meadows"},
    ),
)


def main() -> int:
    """Create every demo entry that is still missing."""
    config = load_config(ROOT / "portfolio" / "config.json")
    for draft in ENTRIES:
        try:
            entry = create_entry(config, draft)
        except EntryError as exc:
            print(f"skipped: {exc}")
            continue
        print(f"created: {entry.entry_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
