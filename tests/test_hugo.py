"""Tests for :mod:`pfm.hugo` (roadmap V9)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pfm.create import Draft, create_entry
from pfm.frontmatter import read_document, render
from pfm.hugo import hugo_checks, normalise_entry, normalize_portfolio
from tests.helpers import make_config


class HugoNormaliseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "content").mkdir()
        self.config = make_config(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, metadata: dict[str, object], body: str = "# T\n") -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(metadata, body), encoding="utf-8")
        return path

    def test_normalise_sets_draft_flag(self) -> None:
        path = self.write(
            "content/technology/computer-science/projects/a.md",
            {"title": "A", "type": "project", "date": "2026-01-01", "status": "draft"},
        )
        entry, changed = normalise_entry(path, self.root)
        self.assertTrue(changed)
        self.assertIs(entry.metadata["draft"], True)
        self.assertEqual(entry.body, "# T\n")

    def test_normalise_is_idempotent(self) -> None:
        create_entry(
            self.config,
            Draft(
                content_type="project",
                title="Clean",
                domain="technology",
                subdomain="computer-science",
            ),
        )
        path = next((self.root / "content").rglob("clean.md"))
        _, changed = normalise_entry(path, self.root)
        self.assertFalse(changed)

    def test_normalize_portfolio_writes(self) -> None:
        path = self.write(
            "content/technology/computer-science/projects/a.md",
            {"title": "A", "type": "project", "date": "2026-01-01", "status": "published"},
        )
        changed = normalize_portfolio(self.config)
        self.assertEqual(changed, ["content/technology/computer-science/projects/a.md"])
        metadata, _ = read_document(path.read_text(encoding="utf-8"))
        self.assertIs(metadata["draft"], False)

    def test_normalize_dry_run(self) -> None:
        path = self.write(
            "content/technology/computer-science/projects/a.md",
            {"title": "A", "type": "project", "date": "2026-01-01", "status": "published"},
        )
        changed = normalize_portfolio(self.config, dry_run=True)
        self.assertTrue(changed)
        metadata, _ = read_document(path.read_text(encoding="utf-8"))
        self.assertNotIn("draft", metadata)


class HugoCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "content").mkdir()
        self.config = make_config(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, metadata: dict[str, object]) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(metadata, "# T\n"), encoding="utf-8")

    def codes(self) -> list[str]:
        return [issue.code for issue in hugo_checks(self.config)]

    def good(self, **overrides: object) -> dict[str, object]:
        metadata: dict[str, object] = {
            "title": "A",
            "type": "project",
            "date": "2026-01-01",
            "status": "published",
            "draft": False,
            "tags": [],
            "domain": "technology",
            "subdomain": "computer-science",
        }
        metadata.update(overrides)
        return metadata

    def test_clean_entry(self) -> None:
        self.write("content/technology/computer-science/projects/a.md", self.good())
        self.assertEqual(hugo_checks(self.config), [])

    def test_unknown_type(self) -> None:
        self.write("content/technology/computer-science/projects/a.md", self.good(type="misc"))
        self.assertIn("H001", self.codes())

    def test_missing_title(self) -> None:
        metadata = self.good()
        del metadata["title"]
        self.write("content/technology/computer-science/projects/a.md", metadata)
        self.assertIn("H002", self.codes())

    def test_bad_date(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md", self.good(date="January 2026")
        )
        self.assertIn("H003", self.codes())

    def test_draft_must_be_boolean(self) -> None:
        self.write("content/technology/computer-science/projects/a.md", self.good(draft="no"))
        self.assertIn("H004", self.codes())

    def test_draft_mismatch(self) -> None:
        self.write("content/technology/computer-science/projects/a.md", self.good(draft=True))
        self.assertIn("H005", self.codes())

    def test_missing_bundle_pdf(self) -> None:
        self.write(
            "content/society/political-science/publications/a.md",
            self.good(
                type="publication",
                domain="society",
                subdomain="political-science",
                pdf="missing.pdf",
            ),
        )
        self.assertIn("H006", self.codes())

    def test_unknown_keys_warn(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md",
            self.good(custom_key="value"),
        )
        issues = hugo_checks(self.config)
        self.assertIn("H007", [issue.code for issue in issues if not issue.is_error])

    def test_published_and_draft(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md",
            self.good(status="published", draft=True),
        )
        codes = self.codes()
        self.assertIn("H005", codes)


if __name__ == "__main__":
    unittest.main()
