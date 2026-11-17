"""Tests for :mod:`pfm.prompts` (roadmap V3, guided prompts and menu)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pfm.prompts import MENU_LABELS, choose, prompt_new_entry, prompt_status, run_menu
from tests.helpers import make_config


class Scripted:
    """A scripted ``input()`` replacement that records the prompts."""

    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


class Collect:
    """A ``print`` replacement that keeps every line."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, message: str) -> None:
        self.lines.append(str(message))

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


class PromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = make_config(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_choose_by_number(self) -> None:
        writer = Collect()
        result = choose("Pick", ["a", "b"], reader=Scripted("2"), writer=writer)
        self.assertEqual(result, "b")
        self.assertIn("1. a", writer.text)

    def test_choose_by_value(self) -> None:
        result = choose("Pick", ["a", "b"], reader=Scripted("b"), writer=Collect())
        self.assertEqual(result, "b")

    def test_choose_retries_on_invalid_input(self) -> None:
        writer = Collect()
        reader = Scripted("9", "zzz", "1")
        self.assertEqual(choose("Pick", ["a", "b"], reader=reader, writer=writer), "a")
        self.assertIn("Invalid choice", writer.text)

    def test_choose_default_on_empty_answer(self) -> None:
        result = choose("Pick", ["a", "b"], default="b", reader=Scripted(""), writer=Collect())
        self.assertEqual(result, "b")

    def test_choose_eof_uses_default(self) -> None:
        result = choose("Pick", ["a", "b"], reader=Scripted(), writer=Collect())
        self.assertEqual(result, "a")

    def test_prompt_new_entry(self) -> None:
        writer = Collect()
        # content type, title, domain, subdomain, tags, date, status,
        # repository, demo
        reader = Scripted("", "My project", "technology", "computer-science", "", "", "", "", "")
        draft = prompt_new_entry(self.config, reader=reader, writer=writer)

        self.assertEqual(draft.content_type, "project")
        self.assertEqual(draft.title, "My project")
        self.assertEqual(draft.domain, "technology")
        self.assertEqual(draft.subdomain, "computer-science")
        self.assertEqual(draft.status, "draft")
        self.assertEqual(draft.tags, ["technology", "computer-science", "project"])
        self.assertEqual(draft.extras, {})

    def test_prompt_new_entry_requires_a_title(self) -> None:
        writer = Collect()
        reader = Scripted(
            "publication",
            "",
            "  ",
            "Real title",
            "society",
            "sociology",
            "a,b",
            "2026",
            "published",
            "",
            "",
        )
        draft = prompt_new_entry(self.config, reader=reader, writer=writer)
        self.assertEqual(draft.title, "Real title")
        self.assertIn("A title is required.", writer.text)

    def test_prompt_new_entry_with_extras(self) -> None:
        # reading fields are pdf, author, source_url
        reader = Scripted(
            "reading",
            "Book notes",
            "society",
            "sociology",
            "osint",
            "2026",
            "",
            "",
            "Umberto Eco",
            "https://example.org/book",
        )
        draft = prompt_new_entry(self.config, reader=reader, writer=Collect())
        self.assertNotIn("pdf", draft.extras)  # empty answers are not kept
        self.assertEqual(draft.extras["author"], "Umberto Eco")
        self.assertEqual(draft.extras["source_url"], "https://example.org/book")
        self.assertEqual(draft.content_type, "reading")

    def test_prompt_status(self) -> None:
        self.assertEqual(prompt_status(reader=Scripted("3"), writer=Collect()), "published")


class MenuTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.config = make_config(Path(self.temp.name))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_menu_dispatches_and_quits(self) -> None:
        calls: list[str] = []
        handlers = {
            "new": lambda: calls.append("new") or 0,
            "list": lambda: calls.append("list") or 0,
            "quit": lambda: 0,
        }
        code = run_menu(
            self.config,
            handlers,
            reader=Scripted("1", "2", "quit"),
            writer=Collect(),
        )
        self.assertEqual(code, 0)
        self.assertEqual(calls, ["new", "list"])

    def test_menu_unknown_action(self) -> None:
        writer = Collect()
        run_menu(self.config, {"quit": lambda: 0}, reader=Scripted("nope", "0"), writer=writer)
        self.assertIn("Unknown action", writer.text)

    def test_menu_blank_line_is_ignored(self) -> None:
        writer = Collect()
        code = run_menu(self.config, {"quit": lambda: 0}, reader=Scripted("", "0"), writer=writer)
        self.assertEqual(code, 0)

    def test_menu_eof_quits(self) -> None:
        code = run_menu(self.config, {"quit": lambda: 0}, reader=Scripted(), writer=Collect())
        self.assertEqual(code, 0)

    def test_menu_survives_a_failing_handler(self) -> None:
        def boom() -> int:
            raise RuntimeError("kaboom")

        writer = Collect()
        run_menu(
            self.config, {"new": boom, "quit": lambda: 0}, reader=Scripted("1", "0"), writer=writer
        )
        self.assertIn("kaboom", writer.text)

    def test_menu_labels_cover_every_command(self) -> None:
        actions = {action for action, _ in MENU_LABELS}
        self.assertEqual(
            actions,
            {"new", "list", "update", "check", "stats", "index", "serve", "quit"},
        )


if __name__ == "__main__":
    unittest.main()
