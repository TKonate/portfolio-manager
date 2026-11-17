"""Tests for :mod:`pfm.index` (roadmap V8)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pfm.create import Draft, create_entry
from pfm.index import GENERATED_MARKER, generate_indexes
from tests.helpers import make_config


class IndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "content").mkdir()
        self.config = make_config(self.root)
        self.project = create_entry(
            self.config,
            Draft(
                content_type="project",
                title="Portfolio Manager",
                domain="technology",
                subdomain="computer-science",
                tags=["python"],
                status="published",
                date="2026-01-01",
            ),
        )
        self.draft = create_entry(
            self.config,
            Draft(
                content_type="publication",
                title="Draft paper",
                domain="technology",
                subdomain="computer-science",
                status="draft",
                date="2026-02-01",
            ),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_generates_four_levels(self) -> None:
        files = generate_indexes(self.config)
        relative = [path.relative_to(self.root).as_posix() for path in files]
        self.assertIn("content/_index.md", relative)
        self.assertIn("content/technology/_index.md", relative)
        self.assertIn("content/technology/computer-science/_index.md", relative)
        self.assertIn("content/technology/computer-science/projects/_index.md", relative)
        self.assertIn("content/technology/computer-science/publications/_index.md", relative)

    def test_type_index_lists_entries_with_links(self) -> None:
        generate_indexes(self.config)
        text = self.text(self.root / "content/technology/computer-science/projects/_index.md")
        self.assertIn(GENERATED_MARKER, text)
        self.assertIn("[Portfolio Manager](portfolio-manager.md)", text)
        self.assertIn("2026-01-01", text)
        self.assertIn("`python`", text)

    def test_drafts_are_marked_and_can_be_excluded(self) -> None:
        generate_indexes(self.config)
        text = self.text(self.root / "content/technology/computer-science/publications/_index.md")
        self.assertIn("*(draft)*", text)

        generate_indexes(self.config, include_drafts=False)
        text = self.text(self.root / "content/technology/computer-science/publications/_index.md")
        self.assertNotIn("Draft paper", text)

    def test_hugo_links(self) -> None:
        generate_indexes(self.config, link_style="hugo")
        text = self.text(self.root / "content/technology/computer-science/projects/_index.md")
        self.assertIn("(/technology/computer-science/projects/portfolio-manager/)", text)

    def test_bundle_link_uses_directory(self) -> None:
        create_entry(
            self.config,
            Draft(
                content_type="publication",
                title="Bundled",
                domain="technology",
                subdomain="computer-science",
                date="2026-03-01",
                bundle=True,
            ),
        )
        generate_indexes(self.config)
        text = self.text(self.root / "content/technology/computer-science/publications/_index.md")
        self.assertIn("[Bundled](bundled/index.md)", text)

    def test_dry_run_writes_nothing(self) -> None:
        files = generate_indexes(self.config, dry_run=True)
        self.assertTrue(files)
        for path in files:
            self.assertFalse(path.exists())

    def test_index_front_matter(self) -> None:
        generate_indexes(self.config)
        text = self.text(self.root / "content/_index.md")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("type: index", text)
        self.assertIn("draft: false", text)

    def test_invalid_link_style(self) -> None:
        with self.assertRaises(ValueError):
            generate_indexes(self.config, link_style="fancy")

    def test_indexes_are_idempotent(self) -> None:
        generate_indexes(self.config)
        first = self.text(self.root / "content/technology/_index.md")
        generate_indexes(self.config)
        self.assertEqual(first, self.text(self.root / "content/technology/_index.md"))

    def test_index_files_are_not_entries(self) -> None:
        generate_indexes(self.config)
        from pfm.store import iter_entries

        self.assertEqual(len(iter_entries(self.root)), 2)


if __name__ == "__main__":
    unittest.main()
