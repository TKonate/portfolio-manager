"""Regression tests for the shipped demonstration portfolio.

These tests guard two things that broke once and are easy to break again:

* the demo portfolio must actually be in the repository (``portfolio/`` at the
  root is git-ignored, ``examples/portfolio/`` must not be);
* it must stay clean: the tool's own checker and statistics must accept it.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from pfm.check import run_checks
from pfm.config import load_config
from pfm.index import generate_indexes
from pfm.stats import collect_stats


class ExamplePortfolioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = Path(__file__).resolve().parent.parent
        cls.config_path = cls.repo / "examples" / "portfolio" / "config.json"

    def test_configuration_is_present(self) -> None:
        self.assertTrue(self.config_path.is_file(), "examples/portfolio/config.json is missing")

    def test_configuration_points_at_the_demo_root(self) -> None:
        config = load_config(self.config_path)
        self.assertEqual(config.portfolio_root, self.repo / "examples" / "portfolio")

    def test_entries_are_present(self) -> None:
        config = load_config(self.config_path)
        stats = collect_stats(config)
        self.assertGreaterEqual(stats.total, 6)
        self.assertIn("project", stats.by_type)
        self.assertIn("lab", stats.by_type)
        self.assertIn("publication", stats.by_type)
        self.assertIn("reading", stats.by_type)

    def test_demo_is_clean(self) -> None:
        config = load_config(self.config_path)
        report = run_checks(config)
        self.assertTrue(report.ok(strict=True), report.to_dict())
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_indexes_exist(self) -> None:
        config = load_config(self.config_path)
        files = generate_indexes(config, dry_run=True)
        self.assertGreaterEqual(len(files), 4)
        for path in files:
            self.assertTrue(path.is_file(), f"missing generated index: {path}")

    def test_page_bundle_with_pdf(self) -> None:
        root = self.repo / "examples" / "portfolio" / "content" / "society" / "political-science"
        bundles = list((root / "publications").glob("*/index.md"))
        self.assertTrue(bundles, "the demo page bundle is missing")
        bundle = bundles[0]
        self.assertTrue(list(bundle.parent.glob("*.pdf")), "the bundle has no PDF attached")


if __name__ == "__main__":
    unittest.main()
