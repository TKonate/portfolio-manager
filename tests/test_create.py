"""Tests for :mod:`pfm.create` and :mod:`pfm.store`."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pfm.create import Draft, build_entry, build_metadata, create_entry, suggest_tags
from pfm.errors import EntryError, EntryNotFoundError, UnsafePathError, ValidationError
from pfm.frontmatter import read_document
from pfm.models import Entry
from pfm.store import (
    entry_id_for,
    is_entry_file,
    iter_entries,
    iter_entries_strict,
    read_entry,
    resolve_entry_id,
    write_entry,
)
from tests.helpers import make_config


class DraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "content").mkdir()
        self.config = make_config(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def draft(self, **overrides: object) -> Draft:
        values: dict[str, object] = {
            "content_type": "project",
            "title": "My project",
            "domain": "technology",
            "subdomain": "computer-science",
        }
        values.update(overrides)
        return Draft(**values)  # type: ignore[arg-type]

    def test_defaults(self) -> None:
        metadata = build_metadata(self.config, self.draft())
        self.assertEqual(metadata["status"], "draft")
        self.assertIs(metadata["draft"], True)
        self.assertEqual(metadata["type"], "project")
        self.assertEqual(metadata["domain"], "technology")
        self.assertEqual(metadata["tags"], [])
        self.assertEqual(len(metadata["date"]), 10)

    def test_default_tags_from_config(self) -> None:
        config = make_config(self.root)
        config.default_tags = ["portfolio"]
        metadata = build_metadata(config, self.draft())
        self.assertEqual(metadata["tags"], ["portfolio"])

    def test_published_sets_draft_false(self) -> None:
        metadata = build_metadata(self.config, self.draft(status="published"))
        self.assertIs(metadata["draft"], False)

    def test_type_specific_fields(self) -> None:
        metadata = build_metadata(
            self.config,
            self.draft(
                extras={
                    "repository": "https://example.org/repo",
                    "demo": "https://example.org/demo",
                    "unknown": "ignored",
                }
            ),
        )
        self.assertEqual(metadata["repository"], "https://example.org/repo")
        self.assertEqual(metadata["demo"], "https://example.org/demo")
        self.assertNotIn("unknown", metadata)

    def test_invalid_type_specific_field(self) -> None:
        with self.assertRaises(ValidationError):
            build_metadata(self.config, self.draft(extras={"repository": "not-a-url"}))

    def test_invalid_domain_and_subdomain(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            build_metadata(self.config, self.draft(domain="nope"))
        self.assertTrue(any("allowed domains" in detail for detail in caught.exception.details))

        with self.assertRaises(ValidationError):
            build_metadata(self.config, self.draft(subdomain="sociology"))

    def test_invalid_title(self) -> None:
        with self.assertRaises(ValidationError):
            build_metadata(self.config, self.draft(title="   "))

    def test_invalid_date(self) -> None:
        with self.assertRaises(ValidationError):
            build_metadata(self.config, self.draft(date="2026-13-01"))

    def test_invalid_status(self) -> None:
        with self.assertRaises(ValidationError):
            build_metadata(self.config, self.draft(status="done"))

    def test_invalid_url(self) -> None:
        with self.assertRaises(ValidationError):
            build_metadata(self.config, self.draft(extras={"repository": "not-a-url"}))

    def test_suggest_tags_uses_default_tags(self) -> None:
        config = make_config(self.root)
        config.default_tags = ["portfolio"]
        tags = suggest_tags(config, self.draft())
        self.assertEqual(tags[0], "portfolio")
        self.assertIn("technology", tags)

    def test_build_entry_path_and_body(self) -> None:
        entry = build_entry(self.config, self.draft(title="Résumé: test"))
        expected = (
            self.root
            / "content"
            / "technology"
            / "computer-science"
            / "projects"
            / "resume-test.md"
        )
        self.assertEqual(entry.path, expected)
        self.assertIn("# Résumé: test", entry.body)

    def test_custom_body_is_kept(self) -> None:
        entry = build_entry(self.config, self.draft(body="# Custom\n"))
        self.assertEqual(entry.body, "# Custom\n")

    def test_create_writes_a_valid_document(self) -> None:
        entry = create_entry(self.config, self.draft())
        self.assertTrue(entry.path.is_file())
        metadata, body = read_document(entry.path.read_text(encoding="utf-8"))
        self.assertEqual(metadata["title"], "My project")
        self.assertIn("# My project", body)

    def test_create_refuses_overwrite(self) -> None:
        create_entry(self.config, self.draft())
        with self.assertRaises(EntryError):
            create_entry(self.config, self.draft())

    def test_create_overwrite(self) -> None:
        first = create_entry(self.config, self.draft())
        second = create_entry(self.config, self.draft(tags=["x"]), overwrite=True)
        self.assertEqual(first.path, second.path)
        metadata, _ = read_document(second.path.read_text(encoding="utf-8"))
        self.assertEqual(metadata["tags"], ["x"])

    def test_bundle_creation(self) -> None:
        entry = create_entry(self.config, self.draft(bundle=True))
        self.assertEqual(entry.path.name, "index.md")
        self.assertEqual(entry.path.parent.name, "my-project")

    def test_bundle_copies_pdf(self) -> None:
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")
        entry = create_entry(
            self.config,
            self.draft(content_type="publication", extras={"pdf": str(pdf)}, bundle=True),
        )
        self.assertTrue((entry.path.parent / "paper.pdf").is_file())
        metadata, _ = read_document(entry.path.read_text(encoding="utf-8"))
        self.assertEqual(metadata["pdf"], "paper.pdf")

    def test_entry_id(self) -> None:
        entry = create_entry(self.config, self.draft())
        self.assertEqual(
            entry.entry_id,
            "content/technology/computer-science/projects/my-project.md",
        )


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "content").mkdir()
        self.config = make_config(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_entry(self, title: str = "Entry", content_type: str = "project") -> Entry:
        return create_entry(
            self.config,
            Draft(
                content_type=content_type,
                title=title,
                domain="technology",
                subdomain="computer-science",
            ),
        )

    def test_is_entry_file(self) -> None:
        self.assertTrue(is_entry_file(Path("slug.md")))
        self.assertFalse(is_entry_file(Path("_index.md")))
        self.assertFalse(is_entry_file(Path(".hidden.md")))
        self.assertFalse(is_entry_file(Path("image.png")))

    def test_iter_entries_skips_indexes(self) -> None:
        entry = self.make_entry()
        (entry.path.parent / "_index.md").write_text("---\ntitle: I\n---\n", encoding="utf-8")
        self.assertEqual(len(iter_entries(self.root)), 1)

    def test_iter_entries_sorted(self) -> None:
        first = self.make_entry("Alpha")
        second = self.make_entry("Beta")
        entries = iter_entries(self.root)
        self.assertEqual([entry.path for entry in entries], sorted([first.path, second.path]))

    def test_broken_entry_is_reported(self) -> None:
        broken = self.root / "content" / "technology" / "computer-science" / "projects" / "bad.md"
        broken.parent.mkdir(parents=True)
        broken.write_text("no front matter", encoding="utf-8")
        entries, failures = iter_entries_strict(self.root)
        self.assertEqual(entries, [])
        self.assertEqual(len(failures), 1)

    def test_write_entry_is_atomic_and_preserves_body(self) -> None:
        entry = self.make_entry()
        entry.body = "# Changed\n"
        write_entry(entry)
        metadata, body = read_document(entry.path.read_text(encoding="utf-8"))
        self.assertEqual(metadata["title"], "Entry")
        self.assertEqual(body.strip(), "# Changed")
        leftovers = list(entry.path.parent.glob(".pfm-*"))
        self.assertEqual(leftovers, [])

    def test_entry_id_for(self) -> None:
        entry = self.make_entry()
        self.assertEqual(entry_id_for(entry.path, self.root), entry.entry_id)

    def test_resolve_entry_id(self) -> None:
        entry = self.make_entry()
        self.assertEqual(resolve_entry_id(self.root, entry.entry_id), entry.path.resolve())

    def test_resolve_rejects_traversal(self) -> None:
        for bad in ("../../etc/passwd", "/etc/passwd", "", "content/../../x"):
            with self.subTest(bad=bad), self.assertRaises(UnsafePathError):
                resolve_entry_id(self.root, bad)

    def test_resolve_missing(self) -> None:
        with self.assertRaises(EntryNotFoundError):
            resolve_entry_id(self.root, "content/missing.md")

    def test_read_entry_invalid_front_matter(self) -> None:
        path = self.root / "content" / "broken.md"
        path.write_text("oops", encoding="utf-8")
        with self.assertRaises(EntryError):
            read_entry(path, self.root)


if __name__ == "__main__":
    unittest.main()
