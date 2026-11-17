"""Hugo / GitHub Pages preparation (roadmap V9).

Hugo is strict about front matter: dates must be parseable, ``draft`` must be a
boolean, and section pages must be named ``_index.md``.  This module provides a
non-destructive normalisation pass plus a Hugo-specific validation report.
"""

from __future__ import annotations

from pathlib import Path

from .check import ERROR, WARNING, Issue
from .config import Config
from .models import TYPE_METADATA_FIELDS, Entry, canonical_metadata, is_valid_type
from .store import iter_entries, read_entry, write_entry
from .validate import ValidationError, validate_date

#: Front matter keys that Hugo understands for the portfolio.
HUGO_KEYS: tuple[str, ...] = (
    "title",
    "date",
    "draft",
    "tags",
    "type",
    "description",
    "slug",
)


def normalise_entry(path: Path, root: Path) -> tuple[Entry, bool]:
    """Normalise one entry for Hugo and return ``(entry, changed)``.

    The normalisation is deliberately conservative:

    * the ``draft`` boolean is recomputed from ``status``;
    * keys are reordered canonically;
    * the body is preserved byte for byte.
    """
    entry = read_entry(path, root)
    metadata = dict(entry.metadata)

    status = str(metadata.get("status", "draft"))
    expected_draft = status != "published"
    changed = False
    if metadata.get("draft") is not expected_draft:
        metadata["draft"] = expected_draft
        changed = True

    if not metadata.get("date"):
        metadata["date"] = "1970-01-01"
        changed = True

    reordered = canonical_metadata(metadata)
    if list(reordered.items()) != list(metadata.items()):
        changed = True

    entry.metadata = reordered
    return entry, changed


def normalize_portfolio(config: Config, *, dry_run: bool = False) -> list[str]:
    """Normalise every entry and return the ids that changed."""
    changed_ids: list[str] = []
    for entry in iter_entries(config.portfolio_root):
        normalised, changed = normalise_entry(entry.path, config.portfolio_root)
        if changed:
            changed_ids.append(normalised.entry_id)
            if not dry_run:
                write_entry(normalised)
    return changed_ids


def hugo_checks(config: Config, *, entries: list[Entry] | None = None) -> list[Issue]:
    """Validate that the portfolio can be rendered by Hugo."""
    if entries is None:
        entries = iter_entries(config.portfolio_root)

    issues: list[Issue] = []
    for entry in entries:
        path = entry.entry_id

        if not is_valid_type(entry.type):
            issues.append(
                Issue("H001", ERROR, path, f"unknown type {entry.type!r}: Hugo has no layout")
            )
        if not entry.title:
            issues.append(Issue("H002", ERROR, path, "missing title: Hugo would use the file name"))

        try:
            validate_date(entry.date)
        except ValidationError as exc:
            issues.append(Issue("H003", ERROR, path, f"date not parseable by Hugo: {exc}"))

        if not isinstance(entry.metadata.get("draft"), bool):
            issues.append(Issue("H004", ERROR, path, "'draft' must be a boolean for Hugo"))
        elif entry.metadata["draft"] != (entry.status != "published"):
            issues.append(
                Issue("H005", ERROR, path, "'draft' and 'status' disagree: run 'pfm hugo --apply'")
            )

        pdf_value = entry.metadata.get("pdf")
        if isinstance(pdf_value, str) and pdf_value and "://" not in pdf_value:
            if not (entry.path.parent / pdf_value).is_file():
                issues.append(
                    Issue("H006", ERROR, path, f"PDF missing from the page bundle: {pdf_value}")
                )

        unknown = [
            key
            for key in entry.metadata
            if key not in HUGO_KEYS
            and key
            not in (
                "status",
                "domain",
                "subdomain",
                *TYPE_METADATA_FIELDS.get(entry.type, ()),
                "author",
            )
        ]
        if unknown:
            issues.append(
                Issue(
                    "H007",
                    WARNING,
                    path,
                    f"non-standard front matter keys: {', '.join(sorted(unknown))}",
                )
            )

        if entry.status == "published" and entry.is_draft:
            issues.append(Issue("H008", ERROR, path, "entry is both published and draft"))

    issues.sort(key=lambda issue: (issue.path, issue.code))
    return issues
