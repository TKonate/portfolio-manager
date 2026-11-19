"""File naming helpers: slugs, tags and target paths.

Every function here is pure: it reads no configuration and touches no disk, so
a name can be computed, compared and tested before the file exists.

Choosing that boundary means this module does not check whether a target path
already exists, nor whether its parent directory is writable:
:func:`pfm.create.create_entry` owns both, and turns a collision into a
user-facing error.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .models import CONTENT_FOLDERS

#: Maximum length of a generated file name, extension excluded.
MAX_SLUG_LENGTH = 80

#: Characters accepted by a slug.
_SLUG_SEPARATORS = re.compile(r"[^a-z0-9]+")

#: A valid slug: lowercase alphanumeric groups joined by single dashes.
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(title: str) -> str:
    """Turn a title into a clean, portable file name.

    Accents are folded to ASCII, everything that is not a letter or a digit is
    collapsed into single dashes, and the result is truncated on a word
    boundary so file names stay readable.

    >>> slugify("Populations civiles et souverainetés fragmentées")
    'populations-civiles-et-souverainetes-fragmentees'
    """
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_SEPARATORS.sub("-", ascii_title).strip("-")
    if len(slug) <= MAX_SLUG_LENGTH:
        return slug

    # Truncate on the last complete word that fits, then strip the separator.
    truncated = slug[:MAX_SLUG_LENGTH]
    if "-" in truncated:
        truncated = truncated.rsplit("-", 1)[0]
    return truncated.strip("-") or slug[:MAX_SLUG_LENGTH].strip("-")


def parse_tags(tags: str | list[str] | tuple[str, ...]) -> list[str]:
    """Normalise a tag input into a deduplicated list.

    Accepts a comma separated string (what the CLI prompt returns) or an
    already split sequence.  Tags are lowercased and internal whitespace is
    replaced by dashes so that the same tag is not counted twice.
    """
    if isinstance(tags, str):
        raw_tags = tags.split(",")
    else:
        raw_tags = list(tags)

    cleaned: list[str] = []
    for raw_tag in raw_tags:
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        tag = re.sub(r"\s+", "-", tag)
        # The allowed punctuation is not decorative: it keeps tags such as
        # ``c++``, ``ci:build`` and ``python3.12`` intact.
        tag = re.sub(r"[^a-z0-9._:+-]", "", tag).strip("-")
        if tag and tag not in cleaned:
            cleaned.append(tag)
    return cleaned


def filename_for(title: str) -> str:
    """Return the Markdown file name for ``title``."""
    slug = slugify(title)
    if not slug:
        raise ValueError("title does not contain any usable character")
    return f"{slug}.md"


def target_path(
    root: Path,
    content_type: str,
    domain: str,
    subdomain: str,
    filename: str,
    *,
    bundle: bool = False,
) -> Path:
    """Build the absolute path of a new entry.

    Layout::

        <root>/content/<domain>/<subdomain>/<type folder>/<filename>

    With ``bundle=True`` (Hugo page bundle, roadmap V9) the entry becomes::

        <root>/content/<domain>/<subdomain>/<type folder>/<slug>/index.md

    Args:
        root: Portfolio root (the directory that contains ``content/``).
        content_type: One of :data:`pfm.models.CONTENT_TYPES`.
        domain: Domain directory name.
        subdomain: Subdomain directory name.
        filename: File name, usually produced by :func:`filename_for`.
        bundle: Create a page bundle directory instead of a single file.

    Raises:
        ValueError: If ``content_type`` is unknown.
    """
    folder = CONTENT_FOLDERS[content_type]
    directory = root / "content" / domain / subdomain / folder
    if bundle:
        slug = Path(filename).stem
        return directory / slug / "index.md"
    return directory / filename


def is_slug_filename(filename: str) -> bool:
    """True when ``filename`` follows the ``slug.md`` or ``index.md`` convention."""
    path = Path(filename)
    if path.suffix != ".md":
        return False
    if path.stem == "index":
        return True
    return bool(SLUG_PATTERN.match(path.stem))
