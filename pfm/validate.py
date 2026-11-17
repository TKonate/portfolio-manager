"""Validation helpers shared by creation, update and checks.

Each helper raises :class:`pfm.errors.ValidationError` with a list of precise
details so the CLI can print something actionable instead of a bare "invalid".
"""

from __future__ import annotations

import datetime as _dt
import re

from .errors import ValidationError
from .models import STATUSES, TYPE_METADATA_FIELDS, is_valid_status, is_valid_type

#: Maximum accepted title length.
MAX_TITLE_LENGTH = 200

#: Date shapes accepted by the tool: year, year-month or full ISO date.
_DATE_SHAPES = (
    re.compile(r"^\d{4}$"),
    re.compile(r"^\d{4}-\d{2}$"),
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),
)

#: Fields that must look like an absolute web URL.
URL_FIELDS = ("repository", "demo", "dataset", "source_url")

#: Fields that may be either a web URL or a repository-relative path.
FILE_OR_URL_FIELDS = ("pdf", "diagram")

_URL_PATTERN = re.compile(r"^https?://[^\s]+$")


def validate_title(title: str) -> str:
    """Return the cleaned title or raise :class:`ValidationError`."""
    cleaned = title.strip()
    if not cleaned:
        raise ValidationError("the title cannot be empty")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise ValidationError(f"the title is too long (max {MAX_TITLE_LENGTH} characters)")
    if "\n" in cleaned or "\r" in cleaned:
        raise ValidationError("the title must be a single line")
    return cleaned


def validate_date(value: str) -> str:
    """Validate a portfolio date (``YYYY``, ``YYYY-MM`` or ``YYYY-MM-DD``)."""
    cleaned = str(value).strip()
    if not cleaned:
        raise ValidationError("the date cannot be empty")
    if not any(shape.match(cleaned) for shape in _DATE_SHAPES):
        raise ValidationError(f"invalid date {cleaned!r}: expected YYYY, YYYY-MM or YYYY-MM-DD")
    if len(cleaned) == 10:
        try:
            _dt.date.fromisoformat(cleaned)
        except ValueError as exc:
            raise ValidationError(f"invalid date {cleaned!r}: {exc}") from exc
    elif len(cleaned) == 7:
        month = int(cleaned[5:7])
        if not 1 <= month <= 12:
            raise ValidationError(f"invalid date {cleaned!r}: month out of range")
    return cleaned


def validate_status(status: str) -> str:
    """Validate a status value."""
    cleaned = status.strip().lower()
    if not is_valid_status(cleaned):
        raise ValidationError(
            f"unknown status: {status!r}",
            [f"allowed statuses: {', '.join(STATUSES)}"],
        )
    return cleaned


def validate_content_type(content_type: str) -> str:
    """Validate a content type value."""
    cleaned = content_type.strip().lower()
    if not is_valid_type(cleaned):
        raise ValidationError(
            f"unknown content type: {content_type!r}",
            [f"allowed types: {', '.join(TYPE_METADATA_FIELDS)}"],
        )
    return cleaned


def validate_url(field: str, value: str) -> str:
    """Validate an absolute ``http(s)`` URL."""
    cleaned = str(value).strip()
    if not _URL_PATTERN.match(cleaned):
        raise ValidationError(f"{field} must be an absolute http(s) URL, got {cleaned!r}")
    return cleaned


def validate_file_or_url(field: str, value: str) -> str:
    """Validate a field that is either an absolute URL or a local path.

    A relative path must stay inside the portfolio.  An absolute path is
    accepted because it is how a local PDF or diagram is *attached* to a page
    bundle; :func:`pfm.create.create_entry` copies it next to ``index.md`` and
    stores only the file name in the front matter.
    """
    cleaned = str(value).strip()
    if _URL_PATTERN.match(cleaned):
        return cleaned
    if "://" in cleaned:
        raise ValidationError(f"{field} must be an http(s) URL or a local path")
    if ".." in cleaned.replace("\\", "/").split("/"):
        raise ValidationError(f"{field} must stay inside the portfolio ('..' segments are refused)")
    return cleaned


def validate_extra_fields(content_type: str, values: dict[str, str]) -> dict[str, str]:
    """Validate the type-specific metadata fields.

    Unknown keys are ignored here: the caller decides what to keep.
    """
    allowed = TYPE_METADATA_FIELDS.get(content_type, ())
    cleaned: dict[str, str] = {}
    for field, value in values.items():
        if field not in allowed or value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        if field in URL_FIELDS:
            cleaned[field] = validate_url(field, text)
        elif field in FILE_OR_URL_FIELDS:
            cleaned[field] = validate_file_or_url(field, text)
        else:
            cleaned[field] = text
    return cleaned
