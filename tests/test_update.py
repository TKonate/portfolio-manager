"""Tests for :mod:`pfm.update` (roadmap V5)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pfm.create import Draft, create_entry
from pfm.errors import EntryError, ValidationError
from pfm.frontmatter import read_document
from pfm.store import iter_entries
from pfm.update import remove_entry, set_status_all, update_entry, update_status
from tests.helpers import make_config


class UpdateEntryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "content").mkdir()
        self.config = make_config(self.root)
        self.entry = create_entry(
            self.config,
            Draft(
                content_type="project",
                title="Portfolio Manager",
                domain="technology",
                subdomain="computer-science",
                tags=["python", "cli"],
                status="draft",
            ),
        )
        # Give the entry a hand-written body and an unknown front matter key.
        text = self.entry.path.read_text(encoding="utf-8")
        text = text.replace("status: draft", "status: draft\ncustom: keep-me")
        text += "\nHand written paragraph.\n"
        self.entry.path.write_text(text, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def reload(self) -> tuple[dict[str, object], str]:
        return read_document(self.entry.path.read_text(encoding="utf-8"))

    def test_status_change_keeps_body_and_unknown_keys(self) -> None:
        result = update_entry(self.config, self.entry.path, status="published")
        metadata, body = self.reload()
        self.assertEqual(metadata["status"], "published")
        self.assertIs(metadata["draft"], False)
        self.assertEqual(metadata["custom"], "keep-me")
        self.assertIn("Hand written paragraph.", body)
        self.assertIn("status", result.changes)
        self.assertIn("draft", result.changes)

    def test_setting_draft_again_flips_flag(self) -> None:
        update_entry(self.config, self.entry.path, status="published")
        update_entry(self.config, self.entry.path, status="draft")
        metadata, _ = self.reload()
        self.assertIs(metadata["draft"], True)

    def test_title_and_date(self) -> None:
        update_entry(self.config, self.entry.path, title="New title", date="2026-02-01")
        metadata, _ = self.reload()
        self.assertEqual(metadata["title"], "New title")
        self.assertEqual(metadata["date"], "2026-02-01")

    def test_tags_replace_add_remove(self) -> None:
        update_entry(self.config, self.entry.path, tags=["a", "b"])
        self.assertEqual(self.reload()[0]["tags"], ["a", "b"])

        update_entry(self.config, self.entry.path, add_tags=["c", "a"])
        self.assertEqual(self.reload()[0]["tags"], ["a", "b", "c"])

        update_entry(self.config, self.entry.path, remove_tags=["b"])
        self.assertEqual(self.reload()[0]["tags"], ["a", "c"])

    def test_fields_set_and_remove(self) -> None:
        update_entry(
            self.config,
            self.entry.path,
            fields={"repository": "https://example.org/repo"},
        )
        self.assertEqual(self.reload()[0]["repository"], "https://example.org/repo")

        update_entry(self.config, self.entry.path, fields={"repository": None})
        self.assertNotIn("repository", self.reload()[0])

    def test_field_empty_string_removes(self) -> None:
        update_entry(self.config, self.entry.path, fields={"repository": "https://example.org/r"})
        update_entry(self.config, self.entry.path, fields={"repository": ""})
        self.assertNotIn("repository", self.reload()[0])

    def test_unknown_field_is_refused(self) -> None:
        with self.assertRaises(ValidationError):
            update_entry(self.config, self.entry.path, fields={"pdf": "x.pdf"})

    def test_invalid_values(self) -> None:
        with self.assertRaises(ValidationError):
            update_entry(self.config, self.entry.path, status="done")
        with self.assertRaises(ValidationError):
            update_entry(self.config, self.entry.path, title="  ")
        with self.assertRaises(ValidationError):
            update_entry(self.config, self.entry.path, date="2026-99-99")

    def test_published_project_warns_without_repository(self) -> None:
        result = update_entry(self.config, self.entry.path, status="published")
        self.assertTrue(any("repository" in warning for warning in result.warnings))

    def test_no_change(self) -> None:
        result = update_entry(self.config, self.entry.path, status="draft")
        self.assertFalse(result.changed)

    def test_dry_run_does_not_write(self) -> None:
        update_entry(self.config, self.entry.path, status="published", dry_run=True)
        self.assertEqual(self.reload()[0]["status"], "draft")

    def test_missing_file(self) -> None:
        with self.assertRaises(EntryError):
            update_entry(self.config, self.root / "nope.md", status="published")

    def test_update_status_helper(self) -> None:
        update_status(self.config, self.entry.path, "in-progress")
        self.assertEqual(self.reload()[0]["status"], "in-progress")

    def test_set_status_all(self) -> None:
        second = create_entry(
            self.config,
            Draft(
                content_type="project",
                title="Second",
                domain="technology",
                subdomain="computer-science",
            ),
        )
        entries = iter_entries(self.root)
        results = set_status_all(self.config, entries, "published")
        self.assertEqual(len(results), 2)
        for entry in (self.entry, second):
            metadata, _ = read_document(entry.path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["status"], "published")

    def test_remove_entry(self) -> None:
        remove_entry(self.config, self.entry.path)
        self.assertFalse(self.entry.path.exists())
        with self.assertRaises(EntryError):
            remove_entry(self.config, self.entry.path)


if __name__ == "__main__":
    unittest.main()
