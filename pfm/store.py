"""Reading, writing and discovering entries on disk.

All disk access for Markdown entries goes through this module:

* :func:`iter_entries` walks ``content/`` and returns parsed entries;
* :func:`read_entry` loads a single file;
* :func:`write_entry` writes it back atomically;
* :func:`resolve_entry_id` turns an untrusted id (web UI, CLI) into a path,
  refusing anything that escapes the portfolio root.

Index files (``_index.md``) and directories/files starting with ``_`` or ``.``
are never returned as entries: they are structure, not content.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

from .errors import EntryError, EntryNotFoundError, UnsafePathError
from .frontmatter import read_document, render
from .models import INDEX_PREFIX, Entry


def is_entry_file(path: Path) -> bool:
    """True when ``path`` looks like a portfolio entry (not an index)."""
    if path.suffix.lower() != ".md":
        return False
    if path.name.startswith(INDEX_PREFIX) or path.name.startswith("."):
        return False
    return True


def read_entry(path: Path, root: Path) -> Entry:
    """Read and parse one Markdown entry.

    Args:
        path: Absolute path of the file.
        root: Portfolio root, used to compute the relative id.

    Raises:
        EntryError: When the file cannot be read or has no valid front matter.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EntryError(f"cannot read {path}: {exc}") from exc
    try:
        metadata, body = read_document(text)
    except EntryError as exc:
        raise EntryError(f"{path}: {exc}") from exc
    return Entry(path=path, root=root, metadata=metadata, body=body)


def write_entry(entry: Entry) -> None:
    """Write ``entry`` back to disk atomically.

    A temporary file is written next to the target and then moved over it, so
    an interrupted run never leaves a half-written portfolio entry.
    """
    entry.path.parent.mkdir(parents=True, exist_ok=True)
    # Exactly one blank line separates the front matter from the body; the
    # body itself is never rewritten.
    document = render(entry.metadata, entry.body, normalize_separator=True)
    handle, temp_name = tempfile.mkstemp(prefix=".pfm-", suffix=".tmp", dir=str(entry.path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(document)
        os.replace(temp_name, entry.path)
    except BaseException:
        # BaseException, not Exception: a Ctrl-C during the write must clean up
        # the temporary file too, otherwise the directory fills with .pfm-*.tmp.
        Path(temp_name).unlink(missing_ok=True)
        raise


def iter_entry_paths(root: Path) -> Iterator[Path]:
    """Yield every entry file under ``<root>/content`` in a stable order."""
    content_root = root / "content"
    if not content_root.is_dir():
        return
    for directory, dirnames, filenames in os.walk(content_root):
        # Skip hidden and underscore-prefixed directories (drafts folders, .git).
        dirnames[:] = sorted(name for name in dirnames if not name.startswith((".", INDEX_PREFIX)))
        for filename in sorted(filenames):
            path = Path(directory) / filename
            if is_entry_file(path):
                yield path


def iter_entries(root: Path) -> list[Entry]:
    """Return every parseable entry of the portfolio, sorted by path.

    Files with broken front matter are surfaced as :class:`EntryError` by
    :func:`iter_entries_strict`; here they are skipped so that one damaged file
    does not break the whole portfolio view.
    """
    entries: list[Entry] = []
    for path in iter_entry_paths(root):
        try:
            entries.append(read_entry(path, root))
        except EntryError:
            continue
    return entries


def iter_entries_strict(root: Path) -> tuple[list[Entry], list[tuple[Path, str]]]:
    """Like :func:`iter_entries` but also return the unreadable files.

    Returns:
        ``(entries, failures)`` where ``failures`` is a list of
        ``(path, message)`` tuples.
    """
    entries: list[Entry] = []
    failures: list[tuple[Path, str]] = []
    for path in iter_entry_paths(root):
        try:
            entries.append(read_entry(path, root))
        except EntryError as exc:
            failures.append((path, str(exc)))
    return entries, failures


def entry_id_for(path: Path, root: Path) -> str:
    """Return the POSIX id of ``path`` relative to the portfolio root."""
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve_entry_id(root: Path, entry_id: str) -> Path:
    """Resolve an untrusted entry id to an absolute path inside ``root``.

    The id is the path relative to the portfolio root, as returned by
    :attr:`pfm.models.Entry.entry_id`.  Absolute paths, ``..`` segments, null
    bytes and symlinks that escape the root are refused.

    Raises:
        UnsafePathError: When the id points outside the portfolio.
        EntryNotFoundError: When the file does not exist.
    """
    if not entry_id or not isinstance(entry_id, str):
        raise UnsafePathError("empty entry id")
    if "\x00" in entry_id:
        raise UnsafePathError("entry id contains a null byte")
    if entry_id.startswith(("/", "\\")):
        raise UnsafePathError(f"entry id must be relative to the portfolio: {entry_id!r}")

    cleaned = entry_id.replace("\\", "/").strip("/")
    if not cleaned:
        raise UnsafePathError("empty entry id")

    root_resolved = root.resolve()
    candidate = (root_resolved / cleaned).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise UnsafePathError(f"entry id escapes the portfolio: {entry_id!r}")
    if not candidate.is_file():
        raise EntryNotFoundError(f"entry not found: {entry_id}")
    return candidate
