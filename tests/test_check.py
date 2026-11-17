"""Tests for :mod:`pfm.check` (roadmap V6)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pfm.check import ERROR, WARNING, format_report, run_checks
from pfm.create import Draft, create_entry
from tests.helpers import make_config


class CheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "content").mkdir()
        self.config = make_config(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(
        self,
        relative: str,
        metadata: dict[str, object] | None = None,
        body: str = "# Title\n",
        raw: str | None = None,
    ) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if raw is not None:
            path.write_text(raw, encoding="utf-8")
            return path
        from pfm.frontmatter import render

        path.write_text(render(metadata or {}, body), encoding="utf-8")
        return path

    def good_metadata(self, **overrides: object) -> dict[str, object]:
        metadata: dict[str, object] = {
            "title": "A project",
            "type": "project",
            "date": "2026-01-15",
            "status": "published",
            "draft": False,
            "tags": ["python"],
            "domain": "technology",
            "subdomain": "computer-science",
            "repository": "https://example.org/repo",
        }
        metadata.update(overrides)
        return metadata

    def codes(self) -> list[str]:
        return [issue.code for issue in run_checks(self.config).issues]

    def test_clean_portfolio(self) -> None:
        self.write("content/technology/computer-science/projects/a.md", self.good_metadata())
        report = run_checks(self.config)
        self.assertTrue(report.ok())
        self.assertEqual(report.checked, 1)
        self.assertEqual(report.issues, [])

    def test_missing_content_directory(self) -> None:
        (self.root / "content").rmdir()
        report = run_checks(self.config)
        self.assertEqual([issue.code for issue in report.issues], ["E001"])
        self.assertFalse(report.ok())

    def test_unreadable_front_matter(self) -> None:
        self.write("content/technology/computer-science/projects/bad.md", raw="no front matter")
        self.assertIn("E001", self.codes())

    def test_missing_title(self) -> None:
        metadata = self.good_metadata()
        del metadata["title"]
        self.write("content/technology/computer-science/projects/a.md", metadata)
        self.assertIn("E002", self.codes())

    def test_invalid_type(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md",
            self.good_metadata(type="article"),
        )
        self.assertIn("E003", self.codes())

    def test_missing_date(self) -> None:
        metadata = self.good_metadata()
        del metadata["date"]
        self.write("content/technology/computer-science/projects/a.md", metadata)
        self.assertIn("E004", self.codes())

    def test_invalid_date(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md",
            self.good_metadata(date="2026-13-40"),
        )
        self.assertIn("E005", self.codes())

    def test_invalid_status(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md",
            self.good_metadata(status="done", draft=True),
        )
        self.assertIn("E006", self.codes())

    def test_draft_flag_must_be_boolean(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md",
            self.good_metadata(draft="false"),
        )
        self.assertIn("E008", self.codes())

    def test_draft_flag_inconsistent(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md",
            self.good_metadata(draft=True),
        )
        self.assertIn("E008", self.codes())

    def test_no_tags_warns(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md",
            self.good_metadata(tags=[]),
        )
        report = run_checks(self.config)
        self.assertIn("W007", [issue.code for issue in report.warnings])
        self.assertTrue(report.ok())
        self.assertFalse(report.ok(strict=True))

    def test_wrong_folder_for_type(self) -> None:
        self.write("content/technology/computer-science/labs/a.md", self.good_metadata())
        self.assertIn("E011", self.codes())

    def test_domain_mismatch(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md",
            self.good_metadata(domain="security"),
        )
        self.assertIn("E011", self.codes())

    def test_unknown_domain_warns(self) -> None:
        self.write(
            "content/space/rockets/projects/a.md",
            self.good_metadata(domain="space", subdomain="rockets"),
        )
        report = run_checks(self.config)
        codes = [issue.code for issue in report.issues]
        self.assertIn("W016", codes)

    def test_filename_convention(self) -> None:
        self.write("content/technology/computer-science/projects/Bad Name.md", self.good_metadata())
        self.assertIn("E012", self.codes())

    def test_index_files_are_ignored(self) -> None:
        self.write(
            "content/technology/computer-science/projects/_index.md", raw="---\ntitle: I\n---\n"
        )
        report = run_checks(self.config)
        self.assertEqual(report.checked, 0)

    def test_missing_pdf(self) -> None:
        self.write(
            "content/society/political-science/publications/a.md",
            self.good_metadata(
                type="publication",
                domain="society",
                subdomain="political-science",
                repository=None,
                pdf="missing.pdf",
            ),
        )
        self.assertIn("E009", self.codes())

    def test_existing_pdf_is_fine(self) -> None:
        path = self.write(
            "content/society/political-science/publications/a.md",
            self.good_metadata(
                type="publication",
                domain="society",
                subdomain="political-science",
                pdf="paper.pdf",
            ),
        )
        (path.parent / "paper.pdf").write_bytes(b"%PDF-1.4")
        self.assertEqual(run_checks(self.config).issues, [])

    def test_published_project_without_repository_warns(self) -> None:
        self.write(
            "content/technology/computer-science/projects/a.md",
            self.good_metadata(repository=None),
        )
        report = run_checks(self.config)
        self.assertIn("W010", [issue.code for issue in report.warnings])

    def test_duplicate_titles(self) -> None:
        self.write("content/technology/computer-science/projects/a.md", self.good_metadata())
        self.write("content/technology/computer-science/projects/b.md", self.good_metadata())
        codes = self.codes()
        self.assertIn("E014", codes)

    def test_entries_created_by_tool_are_clean(self) -> None:
        create_entry(
            self.config,
            Draft(
                content_type="project",
                title="Real entry",
                domain="technology",
                subdomain="computer-science",
                tags=["python"],
                status="published",
                extras={"repository": "https://example.org/repo"},
            ),
        )
        report = run_checks(self.config)
        self.assertTrue(report.ok(), format_report(report))

    def test_format_report(self) -> None:
        self.write("content/technology/computer-science/projects/a.md", raw="broken")
        report = run_checks(self.config)
        text = format_report(report, root=self.root)
        self.assertIn("ERROR", text)
        self.assertIn("0 entries checked", text)

    def test_issue_to_dict(self) -> None:
        self.write("content/technology/computer-science/projects/a.md", raw="broken")
        payload = run_checks(self.config).to_dict()
        self.assertEqual(payload["checked"], 0)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["errors"][0]["code"])

    def test_severity_constants(self) -> None:
        self.assertEqual(ERROR, "error")
        self.assertEqual(WARNING, "warning")


if __name__ == "__main__":
    unittest.main()
