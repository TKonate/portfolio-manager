"""Reading and writing the YAML front matter block.

Portfolio Manager deliberately avoids PyYAML: the front matter it manages is a
small, flat document (strings, booleans and lists of strings).  Supporting
exactly that subset keeps the tool dependency free while staying compatible
with Hugo, GitHub Pages and Obsidian, which all read plain YAML.

The parser is tolerant on input (it accepts single quotes, double quotes,
inline lists and booleans) and predictable on output (canonical key order,
double quoted strings, block lists).
"""

from __future__ import annotations

import re
from typing import Any

from .errors import EntryError

#: Front matter delimiter.
DELIMITER = "---"

#: Dates that can safely be written without quotes (Hugo reads them as dates).
_DATE_PATTERN = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")

#: Characters that can be written without quotes in a plain YAML scalar.
_PLAIN_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9 ._()/@+-]*[A-Za-z0-9._()/@+-])?$")

#: Tokens YAML would read as booleans or null, so they must be quoted.
_AMBIGUOUS_TOKENS = {
    "true",
    "false",
    "yes",
    "no",
    "on",
    "off",
    "null",
    "~",
    "",
}

#: A boolean as written by YAML.
_BOOLEAN_TOKENS = {"true": True, "false": False, "yes": True, "no": False}


def _unescape_double_quoted(value: str) -> str:
    """Unescape the small subset of escapes the serialiser produces."""
    return value.replace('\\"', '"').replace("\\\\", "\\")


def parse_scalar(raw: str) -> Any:
    """Parse a single YAML scalar.

    Handles double quoted strings, single quoted strings, booleans and bare
    strings.  Numbers are kept as strings on purpose: a date such as
    ``2026-01-15`` must stay a string, and no metadata field needs arithmetic.
    """
    value = raw.strip()
    if not value:
        return ""

    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return _unescape_double_quoted(value[1:-1])
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("''", "'")

    lowered = value.lower()
    if lowered in _BOOLEAN_TOKENS:
        return _BOOLEAN_TOKENS[lowered]
    if lowered in {"null", "~"}:
        return None

    # Inline list: [a, b, c]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(item) for item in inner.split(",") if item.strip()]

    return value


def split_document(text: str) -> tuple[str, str]:
    """Split a Markdown document into ``(front_matter_block, body)``.

    Args:
        text: Full file content.

    Returns:
        A tuple with the raw block *without* the delimiters and the body that
        follows the closing delimiter.

    Raises:
        EntryError: When the document has no valid front matter block.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != DELIMITER:
        raise EntryError("missing front matter: the file must start with '---'")

    for index in range(1, len(lines)):
        if lines[index].strip() == DELIMITER:
            return "".join(lines[1:index]), "".join(lines[index + 1 :])

    raise EntryError("unterminated front matter: closing '---' not found")


def loads(block: str) -> dict[str, Any]:
    """Parse a front matter block into an ordered dictionary.

    Supported syntax::

        key: value
        key: "quoted value"
        key: true
        key:
          - first
          - second
        key: [inline, list]

    Raises:
        EntryError: When a line cannot be understood.
    """
    metadata: dict[str, Any] = {}
    pending_key: str | None = None

    for line_number, line in enumerate(block.splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        stripped = line.strip()

        # List item belonging to the previous key.
        if stripped.startswith("- "):
            if pending_key is None:
                raise EntryError(f"line {line_number}: list item without a key")
            current = metadata[pending_key]
            if not isinstance(current, list):
                metadata[pending_key] = []
                current = metadata[pending_key]
            current.append(parse_scalar(stripped[2:]))
            continue

        if ":" not in stripped:
            raise EntryError(f"line {line_number}: expected 'key: value', got {line!r}")

        key, _, raw_value = stripped.partition(":")
        key = key.strip()
        if not key:
            raise EntryError(f"line {line_number}: empty key")

        if raw_value.strip():
            metadata[key] = parse_scalar(raw_value)
            pending_key = None
        else:
            # Empty value: either an empty list or the start of a block list.
            metadata[key] = []
            pending_key = key

    return metadata


def format_scalar(value: Any) -> str:
    """Serialise a scalar value the way Portfolio Manager writes it.

    Plain values stay unquoted (``type: project``, ``date: 2026-01-15``) so the
    files stay readable in Obsidian and on GitHub.  Anything YAML could
    misinterpret — spaces at the edges, colons, quotes, boolean-like words,
    pure numbers — is double quoted.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if _DATE_PATTERN.match(text):
        return text

    is_plain = (
        bool(_PLAIN_PATTERN.match(text))
        and text.lower() not in _AMBIGUOUS_TOKENS
        and not text.replace(".", "").isdigit()
    )
    if is_plain:
        return text

    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def dumps(metadata: dict[str, Any]) -> str:
    """Serialise metadata as a complete front matter block.

    The result starts and ends with ``---`` followed by a newline so it can be
    concatenated directly with a body.

    A ``None`` value is skipped rather than written as ``key: null``, so a
    hand-written null disappears the next time the file is rewritten; an empty
    list is kept as ``key: []`` because it is a meaningful value for ``tags``.
    """
    lines = [DELIMITER]
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            if not value:
                lines.append(f"{key}: []")
                continue
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {format_scalar(item)}")
            continue
        lines.append(f"{key}: {format_scalar(value)}")
    lines.append(DELIMITER)
    return "\n".join(lines) + "\n"


def read_document(text: str) -> tuple[dict[str, Any], str]:
    """Split and parse a Markdown document in one call."""
    block, body = split_document(text)
    return loads(block), body


def render(metadata: dict[str, Any], body: str = "", *, normalize_separator: bool = False) -> str:
    """Render a full Markdown document from metadata and a body.

    Args:
        metadata: Front matter values.
        body: Markdown body.
        normalize_separator: When True (creation path), leading blank lines are
            removed and exactly one blank line separates the front matter from
            the body.  When False (update path) the body is preserved verbatim.
    """
    front = dumps(metadata)
    if not body:
        return front
    if normalize_separator:
        return front + "\n" + body.lstrip("\n")
    return front + body
