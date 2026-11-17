"""Tests for :mod:`pfm.stats` (roadmap V7)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pfm.create import Draft, create_entry
from pfm.stats import collect_stats, compute_stats, format_stats, write_stats_json
from tests.helpers import make_config


class StatsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "content").mkdir()
        self.config = make_config(self.root)

        create_entry(
            self.config,
            Draft(
                content_type="project",
                title="Published project",
                domain="technology",
                subdomain="computer-science",
                tags=["python", "cli"],
                status="published",
                date="2026-01-01",
                extras={"repository": "https://example.org/repo"},
            ),
        )
        create_entry(
            self.config,
            Draft(
                content_type="project",
                title="WIP project",
                domain="technology",
                subdomain="computer-science",
                tags=["python"],
                status="in-progress",
                date="2026-02-01",
            ),
        )
        create_entry(
            self.config,
            Draft(
                content_type="publication",
                title="Paper with PDF",
                domain="society",
                subdomain="political-science",
                tags=["osint"],
                status="published",
                date="2026-03-01",
                extras={"pdf": "paper.pdf"},
                bundle=True,
            ),
        )
        create_entry(
            self.config,
            Draft(
                content_type="reading",
                title="Book notes",
                domain="interdisciplinary",
                subdomain="general",
                tags=[],
                status="draft",
                date="2026",
            ),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_counts(self) -> None:
        stats = collect_stats(self.config)
        self.assertEqual(stats.total, 4)
        self.assertEqual(stats.by_type["project"], 2)
        self.assertEqual(stats.by_status["published"], 2)
        self.assertEqual(stats.by_status["in-progress"], 1)
        self.assertEqual(stats.by_status["draft"], 1)
        self.assertEqual(stats.by_domain["technology"], 2)
        self.assertEqual(stats.drafts, 2)

    def test_tags(self) -> None:
        stats = collect_stats(self.config)
        tags = dict(stats.top_tags)
        self.assertEqual(tags["python"], 2)

    def test_projects_and_publications(self) -> None:
        stats = collect_stats(self.config)
        self.assertEqual(
            [item["title"] for item in stats.published_projects], ["Published project"]
        )
        self.assertEqual([item["title"] for item in stats.projects_in_progress], ["WIP project"])
        self.assertEqual(stats.publications_with_pdf, 1)
        self.assertEqual(stats.publications_without_pdf, 0)

    def test_incomplete(self) -> None:
        stats = collect_stats(self.config)
        ids = [item["id"] for item in stats.incomplete]
        self.assertTrue(any("book-notes" in entry_id for entry_id in ids))

    def test_empty_portfolio(self) -> None:
        stats = compute_stats([])
        self.assertEqual(stats.total, 0)
        self.assertEqual(stats.by_status["draft"], 0)

    def test_format_stats(self) -> None:
        text = format_stats(collect_stats(self.config))
        self.assertIn("By type:", text)
        self.assertIn("Published projects: 1", text)

    def test_to_dict_is_json_serialisable(self) -> None:
        payload = collect_stats(self.config).to_dict()
        json.dumps(payload)
        self.assertEqual(payload["total"], 4)
        self.assertIn("generator", payload)

    def test_write_default_path(self) -> None:
        stats = collect_stats(self.config)
        path = write_stats_json(self.config, stats)
        self.assertEqual(path, self.root / "data" / "portfolio_stats.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["total"], 4)

    def test_write_custom_path(self) -> None:
        destination = self.root / "custom" / "stats.json"
        path = write_stats_json(self.config, collect_stats(self.config), destination)
        self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
