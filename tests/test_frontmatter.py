"""Tests for :mod:`pfm.frontmatter`."""

from __future__ import annotations

import unittest

from pfm.errors import EntryError
from pfm.frontmatter import (
    dumps,
    format_scalar,
    loads,
    parse_scalar,
    read_document,
    render,
    split_document,
)


class SplitDocumentTests(unittest.TestCase):
    def test_splits_front_matter_and_body(self) -> None:
        block, body = split_document("---\ntitle: A\n---\n# Body\n")
        self.assertEqual(block, "title: A\n")
        self.assertEqual(body, "# Body\n")

    def test_missing_front_matter(self) -> None:
        with self.assertRaises(EntryError):
            split_document("# no front matter\n")

    def test_unterminated_front_matter(self) -> None:
        with self.assertRaises(EntryError):
            split_document("---\ntitle: A\n")


class ParseScalarTests(unittest.TestCase):
    def test_double_quoted(self) -> None:
        self.assertEqual(parse_scalar('"hello"'), "hello")
        self.assertEqual(parse_scalar('"say \\"hi\\""'), 'say "hi"')

    def test_single_quoted(self) -> None:
        self.assertEqual(parse_scalar("'hello'"), "hello")
        self.assertEqual(parse_scalar("'it''s'"), "it's")

    def test_booleans(self) -> None:
        self.assertIs(parse_scalar("true"), True)
        self.assertIs(parse_scalar("False"), False)
        self.assertIs(parse_scalar("yes"), True)

    def test_null(self) -> None:
        self.assertIsNone(parse_scalar("null"))
        self.assertIsNone(parse_scalar("~"))

    def test_bare_string_kept_as_string(self) -> None:
        self.assertEqual(parse_scalar("2026-01-15"), "2026-01-15")
        self.assertEqual(parse_scalar("42"), "42")

    def test_inline_list(self) -> None:
        self.assertEqual(parse_scalar("[a, b, c]"), ["a", "b", "c"])
        self.assertEqual(parse_scalar("[]"), [])


class LoadsTests(unittest.TestCase):
    def test_flat_document(self) -> None:
        metadata = loads(
            "title: Test\n"
            "type: project\n"
            "date: 2026-01-15\n"
            "status: published\n"
            "draft: false\n"
            "tags:\n"
            "  - python\n"
            "  - cli\n"
        )
        self.assertEqual(metadata["title"], "Test")
        self.assertEqual(metadata["date"], "2026-01-15")
        self.assertIs(metadata["draft"], False)
        self.assertEqual(metadata["tags"], ["python", "cli"])

    def test_empty_value_becomes_empty_list(self) -> None:
        self.assertEqual(loads("tags:\n"), {"tags": []})

    def test_inline_list_and_comments(self) -> None:
        metadata = loads("# a comment\ntags: [a, b]\n\n")
        self.assertEqual(metadata["tags"], ["a", "b"])

    def test_unknown_key_preserved(self) -> None:
        self.assertEqual(loads("custom: value\n")["custom"], "value")

    def test_invalid_line(self) -> None:
        with self.assertRaises(EntryError):
            loads("not a key value pair\n")

    def test_list_item_without_key(self) -> None:
        with self.assertRaises(EntryError):
            loads("- orphan\n")

    def test_empty_key(self) -> None:
        with self.assertRaises(EntryError):
            loads(": value\n")


class FormatScalarTests(unittest.TestCase):
    def test_plain(self) -> None:
        self.assertEqual(format_scalar("project"), "project")
        self.assertEqual(format_scalar("Portfolio Manager"), "Portfolio Manager")
        self.assertEqual(format_scalar("computer-science"), "computer-science")

    def test_date_unquoted(self) -> None:
        self.assertEqual(format_scalar("2026-01-15"), "2026-01-15")
        self.assertEqual(format_scalar("2026"), "2026")

    def test_ambiguous_words_quoted(self) -> None:
        self.assertEqual(format_scalar("true"), '"true"')
        self.assertEqual(format_scalar("No"), '"No"')
        self.assertEqual(format_scalar(""), '""')

    def test_numbers_quoted(self) -> None:
        self.assertEqual(format_scalar("42"), '"42"')

    def test_urls_and_colons_quoted(self) -> None:
        self.assertEqual(format_scalar("https://example.org/a"), '"https://example.org/a"')
        self.assertEqual(format_scalar("a: b"), '"a: b"')

    def test_booleans(self) -> None:
        self.assertEqual(format_scalar(True), "true")
        self.assertEqual(format_scalar(False), "false")


class DumpsTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        metadata = {
            "title": "Un titre: avec deux points",
            "type": "project",
            "date": "2026-01-15",
            "status": "published",
            "draft": False,
            "tags": ["python", "cli"],
        }
        text = dumps(metadata)
        self.assertTrue(text.startswith("---\n"))
        self.assertTrue(text.endswith("---\n"))
        block, _ = split_document(text)
        parsed = loads(block)
        self.assertEqual(parsed, metadata)

    def test_empty_list(self) -> None:
        self.assertIn("tags: []", dumps({"tags": []}))

    def test_none_values_skipped(self) -> None:
        self.assertNotIn("nothing", dumps({"a": "b", "nothing": None}))


class RenderTests(unittest.TestCase):
    def test_normalise_separator(self) -> None:
        text = render({"title": "A"}, "\n\n# Body", normalize_separator=True)
        self.assertIn("---\n\n# Body", text)

    def test_preserve_body(self) -> None:
        text = render({"title": "A"}, "\n\n# Body")
        self.assertIn("---\n\n\n# Body", text)

    def test_no_body(self) -> None:
        self.assertTrue(render({"title": "A"}).startswith("---\n"))

    def test_read_document(self) -> None:
        metadata, body = read_document("---\ntitle: A\n---\nBody\n")
        self.assertEqual(metadata["title"], "A")
        self.assertEqual(body, "Body\n")


if __name__ == "__main__":
    unittest.main()
