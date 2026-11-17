"""Shared constants and data structures for Portfolio Manager.

The whole tool is built around one idea: a portfolio entry is a Markdown file
whose metadata lives in a small YAML front matter block.  Everything else
(creation, update, checks, statistics, indexes, Hugo export, web UI) is a
transformation of that document.

This module intentionally has no dependency outside the standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Content vocabulary
# ---------------------------------------------------------------------------

#: Content types accepted by the tool (singular, as typed on the command line).
CONTENT_TYPES: tuple[str, ...] = ("project", "lab", "publication", "reading")

#: Directory name used on disk for each content type.
CONTENT_FOLDERS: dict[str, str] = {
    "project": "projects",
    "lab": "labs",
    "publication": "publications",
    "reading": "reading",
}

#: Reverse mapping: directory name -> content type.
FOLDER_CONTENT_TYPES: dict[str, str] = {folder: kind for kind, folder in CONTENT_FOLDERS.items()}

#: Allowed values for the ``status`` field.
STATUSES: tuple[str, ...] = ("draft", "in-progress", "published")

#: Statuses that are considered publicly visible.
PUBLIC_STATUSES: tuple[str, ...] = ("published",)

#: Fallback domain tree, used when ``config.json`` does not define ``domains``.
DEFAULT_DOMAINS: dict[str, list[str]] = {
    "technology": ["computer-science", "electronics"],
    "security": ["cybersecurity", "osint"],
    "society": ["political-science", "sociology"],
    "interdisciplinary": ["general"],
}

#: Type-specific metadata fields (roadmap V4).
TYPE_METADATA_FIELDS: dict[str, tuple[str, ...]] = {
    "project": ("repository", "demo"),
    "lab": ("repository", "dataset", "diagram"),
    "publication": ("pdf", "source_url"),
    "reading": ("pdf", "author", "source_url"),
}

#: Human readable label for each type-specific field.
FIELD_LABELS: dict[str, str] = {
    "repository": "Repository URL",
    "demo": "Demo URL",
    "dataset": "Dataset URL",
    "diagram": "Diagram path or URL",
    "pdf": "PDF path or URL",
    "author": "Author",
    "source_url": "Source URL",
}

#: Canonical order of front matter keys.
#:
#: Unknown keys found in an existing file are preserved after these, in their
#: original order, so hand-written metadata survives an update.
FRONT_MATTER_ORDER: tuple[str, ...] = (
    "title",
    "type",
    "date",
    "status",
    "draft",
    "tags",
    "domain",
    "subdomain",
    "repository",
    "demo",
    "dataset",
    "diagram",
    "pdf",
    "author",
    "source_url",
)

#: Keys that are always written by the tool itself.
REQUIRED_KEYS: tuple[str, ...] = ("title", "type", "date", "status", "tags")

#: Files starting with this prefix are structural (indexes), never entries.
INDEX_PREFIX = "_"

#: Name of the generated index file.
INDEX_FILENAME = "_index.md"

#: Directory holding generated JSON data (statistics for the homepage).
DATA_DIRNAME = "data"


# ---------------------------------------------------------------------------
# Entry model
# ---------------------------------------------------------------------------


@dataclass
class Entry:
    """A portfolio Markdown document loaded from disk.

    Attributes:
        path: Absolute path of the Markdown file.
        root: Absolute path of the portfolio root (the directory containing
            ``content/``).  Kept on the entry so that relative ids can be
            computed without passing the root around.
        metadata: Parsed front matter, insertion ordered.
        body: Markdown body (everything after the closing ``---``).
    """

    path: Path
    root: Path
    metadata: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    # -- convenience accessors -------------------------------------------------

    @property
    def title(self) -> str:
        """Entry title, empty string when missing."""
        return str(self.metadata.get("title", ""))

    @property
    def type(self) -> str:
        """Content type, empty string when missing."""
        return str(self.metadata.get("type", ""))

    @property
    def status(self) -> str:
        """Content status, empty string when missing."""
        return str(self.metadata.get("status", ""))

    @property
    def tags(self) -> list[str]:
        """Tags, always a list (empty when the field is absent or malformed)."""
        value = self.metadata.get("tags", [])
        if isinstance(value, list):
            return [str(tag) for tag in value]
        if isinstance(value, str) and value:
            return [value]
        return []

    @property
    def date(self) -> str:
        """Publication date as written in the front matter, empty when missing."""
        return str(self.metadata.get("date", ""))

    @property
    def domain(self) -> str:
        """Domain, falling back to the first directory below ``content/``."""
        value = self.metadata.get("domain")
        if isinstance(value, str) and value:
            return value
        parts = self.relative_path.parts
        return parts[1] if len(parts) > 2 else ""

    @property
    def subdomain(self) -> str:
        """Subdomain, falling back to the second directory below ``content/``."""
        value = self.metadata.get("subdomain")
        if isinstance(value, str) and value:
            return value
        parts = self.relative_path.parts
        return parts[2] if len(parts) > 3 else ""

    @property
    def is_draft(self) -> bool:
        """True when the entry is not publicly visible."""
        return self.status != "published" or self.metadata.get("draft") is True

    @property
    def relative_path(self) -> Path:
        """Path relative to the portfolio root."""
        try:
            return self.path.relative_to(self.root)
        except ValueError:  # pragma: no cover - defensive, entry always under root
            return self.path

    @property
    def entry_id(self) -> str:
        """Stable identifier: the POSIX path relative to the portfolio root."""
        return self.relative_path.as_posix()

    def to_dict(self) -> dict[str, Any]:
        """Serialise the entry for the JSON API (web UI, statistics)."""
        return {
            "id": self.entry_id,
            "path": str(self.relative_path),
            "title": self.title,
            "type": self.type,
            "status": self.status,
            "draft": self.is_draft,
            "date": self.date,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "tags": self.tags,
            "metadata": {key: value for key, value in self.metadata.items()},
        }


def is_valid_type(content_type: str) -> bool:
    """Return True when ``content_type`` is one of the supported types."""
    return content_type in CONTENT_TYPES


def is_valid_status(status: str) -> bool:
    """Return True when ``status`` is one of :data:`STATUSES`."""
    return status in STATUSES


def type_fields(content_type: str) -> tuple[str, ...]:
    """Type-specific metadata fields for ``content_type``."""
    return TYPE_METADATA_FIELDS.get(content_type, ())


def canonical_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Reorder ``metadata`` following :data:`FRONT_MATTER_ORDER`.

    Unknown keys keep their relative order and are appended at the end, which
    keeps the tool polite with hand-written front matter.
    """
    ordered: dict[str, Any] = {}
    for key in FRONT_MATTER_ORDER:
        if key in metadata:
            ordered[key] = metadata[key]
    for key, value in metadata.items():
        if key not in ordered:
            ordered[key] = value
    return ordered
