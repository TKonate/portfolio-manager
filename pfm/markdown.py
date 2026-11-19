"""A tiny, safe Markdown to HTML renderer used by the web UI preview.

The portfolio is written in a deliberately small Markdown subset (headings,
lists, fenced code, quotes, emphasis and links).  Rendering it here avoids a
Markdown dependency and, more importantly, keeps the preview safe: the input is
HTML-escaped *before* any tag is produced, and only ``http(s)`` links are
turned into anchors.
"""

from __future__ import annotations

import html
import re

_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*(?=\S)(.+?)(?<=\S)\*(?!\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_ORDERED_ITEM = re.compile(r"^\d+\.\s+(.*)$")
_UNORDERED_ITEM = re.compile(r"^[-*+]\s+(.*)$")


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(text, quote=True)


def _safe_url(url: str) -> str | None:
    """Return ``url`` when it is safe to use in an ``href``, else ``None``."""
    lowered = url.strip().lower()
    if lowered.startswith(("http://", "https://", "mailto:", "#", "/", "./", "../")):
        return _escape(url.strip())
    return None


def _inline(text: str) -> str:
    """Render inline Markdown inside an already escaped string."""
    placeholders: list[str] = []

    def stash(fragment: str) -> str:
        placeholders.append(fragment)
        return f"\x00{len(placeholders) - 1}\x00"

    # Code spans are stashed first so their content is never interpreted as
    # Markdown.  NUL is the sentinel because escaped HTML cannot contain it.
    text = _INLINE_CODE.sub(lambda m: stash(f"<code>{m.group(1)}</code>"), text)

    def link(match: re.Match[str]) -> str:
        label, url = match.group(1), match.group(2)
        safe = _safe_url(url)
        if safe is None:
            return label
        return stash(f'<a href="{safe}">{label}</a>')

    text = _LINK.sub(link, text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)

    for index, fragment in enumerate(placeholders):
        text = text.replace(f"\x00{index}\x00", fragment)
    return text


def render_markdown(text: str) -> str:
    """Render a Markdown document to HTML.

    The renderer is intentionally conservative: anything it does not understand
    becomes a paragraph, and raw HTML is escaped rather than passed through.
    """
    lines = text.splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    list_kind: str | None = None
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            output.append(f"<p>{_inline(_escape(' '.join(paragraph)))}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            output.append(f"</{list_kind}>")
            list_kind = None

    for raw_line in lines:
        line = raw_line.rstrip()

        if line.strip().startswith("```"):
            if in_code:
                output.append(f"<pre><code>{_escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                flush_paragraph()
                close_list()
                in_code = True
            continue

        if in_code:
            code_lines.append(raw_line)
            continue

        if not line.strip():
            flush_paragraph()
            close_list()
            continue

        heading = _HEADING.match(line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{_inline(_escape(heading.group(2).strip()))}</h{level}>")
            continue

        if line.strip() in {"---", "***", "___"}:
            flush_paragraph()
            close_list()
            output.append("<hr>")
            continue

        if line.startswith(">"):
            flush_paragraph()
            close_list()
            quote = _inline(_escape(line.lstrip("> ").strip()))
            output.append(f"<blockquote>{quote}</blockquote>")
            continue

        unordered = _UNORDERED_ITEM.match(line.strip())
        ordered = _ORDERED_ITEM.match(line.strip())
        item = unordered or ordered
        if item is not None:
            flush_paragraph()
            kind = "ul" if unordered is not None else "ol"
            if list_kind != kind:
                close_list()
                output.append(f"<{kind}>")
                list_kind = kind
            output.append(f"<li>{_inline(_escape(item.group(1)))}</li>")
            continue

        paragraph.append(line.strip())

    if in_code and code_lines:
        output.append(f"<pre><code>{_escape(chr(10).join(code_lines))}</code></pre>")
    flush_paragraph()
    close_list()
    return "\n".join(output)
