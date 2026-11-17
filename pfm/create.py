"""Entry creation (roadmap V1 to V4, plus Hugo page bundles for V9).

Creation is split in two steps so it can be tested and reused by the web UI:

* :func:`build_entry` validates a draft and returns in-memory metadata + body;
* :func:`create_entry` writes it to disk, refusing to overwrite by default.
"""

from __future__ import annotations

import datetime as _dt
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import templates
from .config import Config
from .errors import EntryError, ValidationError
from .models import CONTENT_FOLDERS, Entry, canonical_metadata
from .naming import filename_for, parse_tags, target_path
from .store import entry_id_for, write_entry
from .validate import (
    validate_content_type,
    validate_date,
    validate_extra_fields,
    validate_status,
    validate_title,
)


@dataclass
class Draft:
    """A content entry the user wants to create.

    Attributes:
        content_type: ``project``, ``lab``, ``publication`` or ``reading``.
        title: Human readable title.
        domain: Domain directory (see :class:`pfm.config.Config`).
        subdomain: Subdomain directory.
        tags: Tags; when empty, defaults are derived (see :func:`suggest_tags`).
        date: ``YYYY``, ``YYYY-MM`` or ``YYYY-MM-DD``; today when empty.
        status: ``draft`` (default), ``in-progress`` or ``published``.
        extras: Type-specific metadata such as ``repository`` or ``pdf``.
        bundle: Create a Hugo page bundle (``<slug>/index.md``) instead of a
            single Markdown file.
        body: Explicit Markdown body; when ``None`` the type template is used.
    """

    content_type: str
    title: str
    domain: str
    subdomain: str
    tags: list[str] = field(default_factory=list)
    date: str = ""
    status: str = "draft"
    extras: dict[str, str] = field(default_factory=dict)
    bundle: bool = False
    body: str | None = None


def default_date() -> str:
    """Return today's date in the portfolio format."""
    return _dt.date.today().isoformat()


def suggest_tags(config: Config, draft: Draft) -> list[str]:
    """Suggested tags for a draft.

    The suggestion combines the configured ``default_tags`` with the domain,
    subdomain and content type: it gives every entry a usable baseline without
    any configuration, and stays predictable.
    """
    candidates = list(config.default_tags)
    candidates.extend([draft.domain, draft.subdomain, draft.content_type])
    return parse_tags(candidates)


def build_metadata(config: Config, draft: Draft) -> dict[str, Any]:
    """Validate ``draft`` and return the front matter it produces.

    Raises:
        ValidationError: With the list of every invalid field.
    """
    content_type = validate_content_type(draft.content_type)
    title = validate_title(draft.title)
    domain = (draft.domain or "").strip().lower()
    subdomain = (draft.subdomain or "").strip().lower()

    details: list[str] = []
    try:
        config.validate_domain(domain)
    except ValidationError as exc:
        details.extend(exc.details or [exc.message])
    else:
        try:
            config.validate_subdomain(domain, subdomain)
        except ValidationError as exc:
            details.extend(exc.details or [exc.message])

    try:
        status = validate_status(draft.status or "draft")
    except ValidationError as exc:
        details.extend(exc.details or [exc.message])
        status = "draft"

    try:
        date = validate_date(draft.date or default_date())
    except ValidationError as exc:
        details.append(exc.message)
        date = draft.date

    try:
        extras = validate_extra_fields(content_type, draft.extras)
    except ValidationError as exc:
        details.append(exc.message)
        extras = {}

    if details:
        raise ValidationError("invalid entry metadata", details)

    # Explicit tags win; otherwise the configured default tags apply.  The
    # domain/subdomain/type suggestion is only used by the interactive prompt,
    # so a scripted entry does not silently gain three tags.
    tags = parse_tags(draft.tags) if draft.tags else parse_tags(config.default_tags)

    metadata: dict[str, Any] = {
        "title": title,
        "type": content_type,
        "date": date,
        "status": status,
        "draft": status != "published",
        "tags": tags,
        "domain": domain,
        "subdomain": subdomain,
    }
    metadata.update(extras)
    return canonical_metadata(metadata)


def build_entry(config: Config, draft: Draft) -> Entry:
    """Build the entry in memory (nothing is written to disk)."""
    metadata = build_metadata(config, draft)
    content_type = str(metadata["type"])
    title = str(metadata["title"])
    body = draft.body if draft.body is not None else templates.body_for(content_type, title)
    filename = filename_for(title)

    path = target_path(
        config.portfolio_root,
        content_type,
        str(metadata["domain"]),
        str(metadata["subdomain"]),
        filename,
        bundle=draft.bundle,
    )
    entry = Entry(path=path, root=config.portfolio_root, metadata=metadata, body=body)
    return entry


def create_entry(config: Config, draft: Draft, *, overwrite: bool = False) -> Entry:
    """Create the entry on disk and return it.

    Args:
        config: Resolved configuration.
        draft: Content to create.
        overwrite: Replace an existing entry instead of failing.

    Raises:
        EntryError: When the target already exists and ``overwrite`` is False.
    """
    entry = build_entry(config, draft)

    if entry.path.exists() and not overwrite:
        raise EntryError(
            f"refusing to overwrite an existing entry: {entry.entry_id} "
            "(use --overwrite if this is really what you want)"
        )

    # Hugo page bundle: attach a local PDF or diagram next to index.md (V9).
    # The front matter must only ever contain a relative path, so an absolute
    # source path is copied in and replaced by its file name.
    for attachment in ("pdf", "diagram"):
        value = entry.metadata.get(attachment)
        if not isinstance(value, str) or not value or "://" in value:
            continue
        source = Path(value).expanduser()
        if not source.is_absolute():
            continue
        if not draft.bundle:
            raise ValidationError(
                f"{attachment} must be a relative path or a URL",
                [f"use --bundle to attach {source.name} to the entry"],
            )
        if not source.is_file():
            raise ValidationError(f"{attachment} file not found: {source}")

        destination = entry.path.parent / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        entry.metadata[attachment] = source.name

    write_entry(entry)
    return entry


def describe_entry(entry: Entry) -> str:
    """Return a short one-line description of ``entry`` (used by the CLI)."""
    folder = CONTENT_FOLDERS.get(entry.type, entry.type)
    tags = ", ".join(entry.tags)
    return (
        f"{entry.title} [{entry.type}/{entry.status}] "
        f"{entry.domain}/{entry.subdomain}/{folder} -> {entry.entry_id} ({tags})"
    )


def entry_id(entry: Entry) -> str:
    """Return the portfolio-relative id of ``entry``."""
    return entry_id_for(entry.path, entry.root)
