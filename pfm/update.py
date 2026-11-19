"""Metadata updates that preserve the Markdown body (roadmap V5).

The update path never regenerates the document: it re-reads the file, changes
the requested front matter keys, reorders them canonically and writes the body
back untouched.  Unknown, hand-written keys are preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import Config
from .errors import EntryError, ValidationError
from .models import TYPE_METADATA_FIELDS, Entry, canonical_metadata
from .naming import parse_tags
from .store import read_entry, write_entry
from .validate import validate_date, validate_extra_fields, validate_status, validate_title


@dataclass
class UpdateResult:
    """Outcome of an update.

    Attributes:
        entry: The updated entry (also written to disk unless ``dry_run``).
        changes: Mapping ``field -> (old value, new value)``.
        warnings: Non blocking remarks, typically "published without repository".
    """

    entry: Entry
    changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        """True when at least one field changed."""
        return bool(self.changes)


def _normalise_tags(values: list[str] | None) -> list[str]:
    return parse_tags(values or [])


def update_entry(
    config: Config,
    path: Path,
    *,
    status: str | None = None,
    title: str | None = None,
    date: str | None = None,
    tags: list[str] | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    fields: dict[str, str | None] | None = None,
    dry_run: bool = False,
) -> UpdateResult:
    """Update selected front matter fields of an entry.

    Args:
        config: Resolved configuration (used for type-specific validation).
        path: File to update.
        status: New status; also keeps ``draft`` consistent.
        title: New title (the file is **not** renamed: do it explicitly).
        date: New date.
        tags: Replace the whole tag list.
        add_tags: Tags to append.
        remove_tags: Tags to remove.
        fields: Type-specific metadata; a ``None`` or empty value removes the
            key, any other value sets it.
        dry_run: Compute the result without writing.

    Raises:
        ValidationError: When one of the values is invalid.
        EntryError: When the file cannot be read or written.
    """
    entry = read_entry(path, config.portfolio_root)
    metadata = dict(entry.metadata)
    changes: dict[str, tuple[Any, Any]] = {}
    warnings: list[str] = []

    if title is not None:
        new_title = validate_title(title)
        if new_title != metadata.get("title"):
            changes["title"] = (metadata.get("title"), new_title)
            metadata["title"] = new_title

    if date is not None:
        new_date = validate_date(date)
        if new_date != metadata.get("date"):
            changes["date"] = (metadata.get("date"), new_date)
            metadata["date"] = new_date

    if status is not None:
        new_status = validate_status(status)
        old_status = metadata.get("status")
        if new_status != old_status:
            changes["status"] = (old_status, new_status)
            metadata["status"] = new_status
        old_draft = metadata.get("draft")
        new_draft = new_status != "published"
        if old_draft != new_draft:
            changes["draft"] = (old_draft, new_draft)
            metadata["draft"] = new_draft

    current_tags = parse_tags(metadata.get("tags", []))
    new_tags = list(current_tags)
    if tags is not None:
        new_tags = _normalise_tags(tags)
    if add_tags:
        for tag in _normalise_tags(add_tags):
            if tag not in new_tags:
                new_tags.append(tag)
    if remove_tags:
        for tag in _normalise_tags(remove_tags):
            if tag in new_tags:
                new_tags.remove(tag)
    if new_tags != current_tags:
        changes["tags"] = (current_tags, new_tags)
        metadata["tags"] = new_tags

    if fields:
        content_type = str(metadata.get("type", entry.type))
        allowed = TYPE_METADATA_FIELDS.get(content_type, ())
        for field_name, value in fields.items():
            if field_name not in allowed:
                # Unlike validate_extra_fields, an explicitly named field that
                # the type does not carry is refused: on the command line it is
                # a typo, not background noise.
                raise ValidationError(
                    f"{field_name!r} is not a metadata field of type {content_type!r}",
                    [f"allowed fields: {', '.join(allowed) or '(none)'}"],
                )
            if value is None or not str(value).strip():
                if field_name in metadata:
                    changes[field_name] = (metadata.get(field_name), None)
                    del metadata[field_name]
                continue
            validated = validate_extra_fields(content_type, {field_name: str(value)})
            new_value = validated.get(field_name)
            if new_value != metadata.get(field_name):
                changes[field_name] = (metadata.get(field_name), new_value)
                metadata[field_name] = new_value

    if metadata.get("status") == "published" and entry.type == "project":
        if not metadata.get("repository"):
            warnings.append("published project without a repository URL (see 'pfm check')")

    entry.metadata = canonical_metadata(metadata)
    if changes and not dry_run:
        write_entry(entry)
    return UpdateResult(entry=entry, changes=changes, warnings=warnings)


def update_status(config: Config, path: Path, status: str) -> UpdateResult:
    """Convenience wrapper for the ``update-status`` command."""
    return update_entry(config, path, status=status)


def set_status_all(
    config: Config, entries: list[Entry], status: str, *, dry_run: bool = False
) -> list[UpdateResult]:
    """Apply one status to many entries (used by the web UI bulk action)."""
    results: list[UpdateResult] = []
    for entry in entries:
        results.append(update_entry(config, entry.path, status=status, dry_run=dry_run))
    return results


def remove_entry(config: Config, path: Path) -> None:
    """Delete an entry file (explicit user action only)."""
    if not path.is_file():
        raise EntryError(f"entry not found: {path}")
    path.unlink()
