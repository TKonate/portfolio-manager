"""Guided prompts and interactive menu (roadmap V3).

Everything here is written against injected ``reader``/``writer`` callables so
the whole flow can be tested without touching ``stdin``/``stdout``.

The prompts are intentionally simple: numbered choices where the value can also
be typed, and every field keeps a sensible default shown in brackets.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Callable, Mapping
from typing import Any

from .config import Config
from .create import Draft, suggest_tags
from .models import CONTENT_TYPES, FIELD_LABELS, STATUSES, type_fields

Reader = Callable[[str], str]
Writer = Callable[[str], None]


def _ask(prompt: str, default: str, reader: Reader) -> str:
    """Ask for a value, returning ``default`` when the answer is empty."""
    suffix = f" [{default}]" if default else ""
    try:
        answer = reader(f"{prompt}{suffix}: ")
    except EOFError:
        return default
    answer = (answer or "").strip()
    return answer or default


def choose(
    title: str,
    options: list[str],
    *,
    default: str | None = None,
    reader: Reader,
    writer: Writer,
    labels: Mapping[str, str] | None = None,
) -> str:
    """Display a numbered list and return the selected option.

    The user can answer with the number or with the value itself.  An empty
    answer selects ``default`` (the first option when no default is given).
    """
    writer(title)
    for index, option in enumerate(options, start=1):
        label = labels.get(option, option) if labels else option
        writer(f"  {index}. {label}")

    fallback = default or (options[0] if options else "")
    while True:
        answer = _ask("Choice", fallback, reader)
        if answer in options:
            return answer
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        writer(f"Invalid choice: {answer!r}. Type a number or one of: {', '.join(options)}")


def prompt_new_entry(
    config: Config,
    *,
    content_type: str | None = None,
    reader: Reader = input,
    writer: Writer = print,
) -> Draft:
    """Ask every field needed to create an entry and return a draft.

    The function only collects values; validation and writing is done by
    :func:`pfm.create.create_entry`, so a bad answer produces one clear error
    instead of a half-created file.
    """
    if content_type is None:
        content_type = choose("Content type:", list(CONTENT_TYPES), reader=reader, writer=writer)

    title = ""
    while not title.strip():
        title = _ask("Title", "", reader)
        if not title.strip():
            writer("A title is required.")

    domain = choose("Domain:", sorted(config.domains), reader=reader, writer=writer)
    subdomain = choose(
        f"Subdomain for {domain}:",
        config.domains[domain],
        reader=reader,
        writer=writer,
    )

    # Tags: the suggestion is shown as the default, which makes the common case
    # a single Enter keypress.
    draft_for_suggestion = Draft(
        content_type=content_type,
        title=title,
        domain=domain,
        subdomain=subdomain,
    )
    suggested_tags = ", ".join(suggest_tags(config, draft_for_suggestion))
    tags_answer = _ask("Tags, separated by commas", suggested_tags, reader)
    tags = [tag.strip() for tag in tags_answer.split(",") if tag.strip()]

    date = _ask("Date", _dt.date.today().isoformat(), reader)
    status = choose("Status:", list(STATUSES), default="draft", reader=reader, writer=writer)

    extras: dict[str, Any] = {}
    for field in type_fields(content_type):
        label = FIELD_LABELS.get(field, field)
        answer = _ask(f"{label} (optional)", "", reader)
        if answer:
            extras[field] = answer

    return Draft(
        content_type=content_type,
        title=title,
        domain=domain,
        subdomain=subdomain,
        tags=tags,
        date=date,
        status=status,
        extras=extras,
    )


def prompt_status(*, reader: Reader = input, writer: Writer = print) -> str:
    """Ask for a status (used by ``update`` when no flag is given)."""
    return choose("New status:", list(STATUSES), reader=reader, writer=writer)


MENU_LABELS: tuple[tuple[str, str], ...] = (
    ("new", "New entry"),
    ("list", "List entries"),
    ("update", "Update an entry"),
    ("check", "Check portfolio"),
    ("stats", "Statistics"),
    ("index", "Generate indexes"),
    ("serve", "Open the web UI"),
    ("quit", "Quit"),
)


def run_menu(
    config: Config,
    handlers: Mapping[str, Callable[[], int | None]],
    *,
    reader: Reader = input,
    writer: Writer = print,
) -> int:
    """Run the interactive menu until the user quits.

    Args:
        config: Resolved configuration (only used for the banner).
        handlers: Mapping ``action -> callable``.  Unknown actions are ignored.
        reader: Input callable (injectable for tests).
        writer: Output callable.
    """
    actions = [action for action, _ in MENU_LABELS if action in handlers]
    labels = {action: label for action, label in MENU_LABELS}

    while True:
        writer("")
        writer(f"Portfolio Manager — {config.portfolio_root}")
        for index, action in enumerate(actions, start=1):
            writer(f"  {index}. {labels[action]}")
        writer("")

        try:
            answer = reader("Action: ").strip()
        except EOFError:
            return 0

        if not answer:
            continue
        if answer.isdigit() and 1 <= int(answer) <= len(actions):
            action = actions[int(answer) - 1]
        else:
            action = answer.lower()

        if action in {"quit", "q", "exit", "0"}:
            return 0
        handler = handlers.get(action)
        if handler is None:
            writer(f"Unknown action: {action}")
            continue
        try:
            handler()
        except Exception as exc:  # the menu must survive a failing action
            writer(f"Error: {exc}")
