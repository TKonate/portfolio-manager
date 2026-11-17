"""End-to-end tests for the command line interface."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from pfm.cli import ALIASES, EXIT_ERROR, EXIT_OK, build_parser, main
from tests.helpers import make_sandbox, run_cli


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp, self.sandbox = make_sandbox()
        self.config_path = self.sandbox.config_path
        self.root = self.sandbox.root

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str) -> tuple[int, str, str]:
        return run_cli(list(args), self.config_path)

    def create(self, *extra: str) -> str:
        code, out, err = self.cli(
            "new",
            "project",
            "--no-input",
            "-T",
            "Portfolio Manager",
            "-d",
            "technology",
            "-s",
            "computer-science",
            *extra,
        )
        self.assertEqual(code, EXIT_OK, err)
        return out.strip().splitlines()[0].replace("Created ", "")

    # -- parser ------------------------------------------------------------

    def test_parser_has_every_command(self) -> None:
        actions = build_parser()._subparsers._group_actions  # type: ignore[attr-defined]
        names = set(actions[0].choices)  # type: ignore[index]
        for expected in (
            "init",
            "new",
            "list",
            "show",
            "update",
            "update-status",
            "check",
            "stats",
            "index",
            "hugo",
            "serve",
            "menu",
        ):
            self.assertIn(expected, names)

    def test_version_flag(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            build_parser().parse_args(["--version"])
        self.assertEqual(caught.exception.code, 0)

    def test_aliases_point_to_real_commands(self) -> None:
        actions = build_parser()._subparsers._group_actions  # type: ignore[attr-defined]
        choices = set(actions[0].choices)  # type: ignore[index]
        for alias, target in ALIASES.items():
            self.assertIn(target, choices, alias)

    # -- init --------------------------------------------------------------

    def test_init_creates_skeleton_and_config(self) -> None:
        target = self.sandbox.directory / "fresh"
        config_path = self.sandbox.directory / "fresh-config.json"
        code, out, _ = run_cli(["init", str(target)], config_path)
        self.assertEqual(code, EXIT_OK)
        self.assertTrue((target / "content").is_dir())
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["portfolio_root"], "fresh")
        self.assertIn("portfolio created", out)

    def test_init_refuses_to_overwrite_config(self) -> None:
        target = self.sandbox.directory / "fresh"
        config_path = self.sandbox.directory / "fresh-config.json"
        run_cli(["init", str(target)], config_path)
        code, _, err = run_cli(["init", str(target)], config_path)
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("already exists", err)

    # -- new ---------------------------------------------------------------

    def test_new_creates_entry(self) -> None:
        entry_id = self.create(
            "--tags", "python,cli", "--status", "published", "--repository", "https://example.org/r"
        )
        self.assertEqual(
            entry_id, "content/technology/computer-science/projects/portfolio-manager.md"
        )
        text = (self.root / entry_id).read_text(encoding="utf-8")
        self.assertIn("status: published", text)
        self.assertIn('repository: "https://example.org/r"', text)

    def test_new_requires_title_in_non_interactive_mode(self) -> None:
        code, _, err = self.cli("new", "project", "--no-input")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("title is required", err)

    def test_new_requires_type(self) -> None:
        code, _, err = self.cli("new", "--no-input", "-T", "No type")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("content type is required", err)

    def test_new_rejects_invalid_domain_with_details(self) -> None:
        code, _, err = self.cli(
            "new", "project", "--no-input", "-T", "X", "-d", "space", "-s", "rockets"
        )
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("allowed domains", err)

    def test_new_refuses_duplicate(self) -> None:
        self.create()
        code, _, err = self.cli(
            "new",
            "project",
            "--no-input",
            "-T",
            "Portfolio Manager",
            "-d",
            "technology",
            "-s",
            "computer-science",
        )
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("refusing to overwrite", err)

    def test_new_overwrite(self) -> None:
        self.create()
        code, _, err = self.cli(
            "new",
            "project",
            "--no-input",
            "-T",
            "Portfolio Manager",
            "-d",
            "technology",
            "-s",
            "computer-science",
            "--overwrite",
            "--tags",
            "new",
        )
        self.assertEqual(code, EXIT_OK, err)

    def test_new_bundle_with_body_file(self) -> None:
        body = self.sandbox.directory / "body.md"
        body.write_text("# Custom body\n", encoding="utf-8")
        code, out, err = self.cli(
            "new",
            "lab",
            "--no-input",
            "-T",
            "Bench",
            "-d",
            "technology",
            "-s",
            "computer-science",
            "--bundle",
            "--body-file",
            str(body),
        )
        self.assertEqual(code, EXIT_OK, err)
        entry_id = out.splitlines()[0].replace("Created ", "")
        self.assertIn("bench/index.md", entry_id)
        self.assertIn("# Custom body", (self.root / entry_id).read_text(encoding="utf-8"))

    def test_new_alias(self) -> None:
        code, out, err = self.cli(
            "n",
            "project",
            "--no-input",
            "-T",
            "Alias",
            "-d",
            "technology",
            "-s",
            "computer-science",
            "-q",
        )
        self.assertEqual(code, EXIT_OK, err)
        self.assertEqual(out, "")

    def test_new_quiet(self) -> None:
        code, out, _ = self.cli(
            "new",
            "project",
            "--no-input",
            "-T",
            "Quiet",
            "-d",
            "technology",
            "-s",
            "computer-science",
            "-q",
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.strip(), "")

    # -- list / show -------------------------------------------------------

    def test_list_text_and_json(self) -> None:
        self.create()
        code, out, _ = self.cli("list")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Portfolio Manager", out)
        self.assertIn("id: content/technology/computer-science/projects/portfolio-manager.md", out)

        code, out, _ = self.cli("list", "--json")
        payload = json.loads(out)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["title"], "Portfolio Manager")

    def test_list_filters(self) -> None:
        self.create("--status", "published")
        self.assertEqual(self.cli("list", "--status", "draft")[1].strip(), "No entry matches.")
        self.assertEqual(
            json.loads(self.cli("list", "--type", "project", "--json")[1])[0]["status"], "published"
        )
        self.assertEqual(self.cli("list", "--domain", "security")[1].strip(), "No entry matches.")
        self.assertEqual(self.cli("list", "--tag", "nope")[1].strip(), "No entry matches.")

    def test_show(self) -> None:
        entry_id = self.create()
        code, out, _ = self.cli("show", entry_id)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("title: Portfolio Manager", out)

    def test_show_missing(self) -> None:
        code, _, err = self.cli("show", "content/missing.md")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("not found", err)

    def test_show_blocks_traversal(self) -> None:
        code, _, err = self.cli("show", "../../etc/passwd")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("escapes", err)

    # -- update ------------------------------------------------------------

    def test_update_status(self) -> None:
        entry_id = self.create()
        code, out, _ = self.cli("update-status", entry_id, "published")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("status -> published", out)
        self.assertIn("status: published", (self.root / entry_id).read_text(encoding="utf-8"))

    def test_update_fields_and_tags(self) -> None:
        entry_id = self.create()
        code, out, _ = self.cli(
            "update",
            entry_id,
            "--status",
            "published",
            "--add-tag",
            "featured",
            "--repository",
            "https://example.org/repo",
        )
        self.assertEqual(code, EXIT_OK)
        self.assertIn("repository", out)
        text = (self.root / entry_id).read_text(encoding="utf-8")
        self.assertIn("featured", text)
        self.assertIn('repository: "https://example.org/repo"', text)

    def test_update_dry_run(self) -> None:
        entry_id = self.create()
        code, out, _ = self.cli("update", entry_id, "--status", "published", "--dry-run")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Would update", out)
        self.assertIn("status: draft", (self.root / entry_id).read_text(encoding="utf-8"))

    def test_update_nothing_to_do(self) -> None:
        entry_id = self.create()
        code, out, _ = self.cli("update", entry_id)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Nothing to update", out)

    def test_update_remove_field(self) -> None:
        entry_id = self.create("--repository", "https://example.org/repo")
        code, _, err = self.cli("update", entry_id, "--remove-field", "repository")
        self.assertEqual(code, EXIT_OK, err)
        self.assertNotIn("repository", (self.root / entry_id).read_text(encoding="utf-8"))

    def test_update_invalid_status_is_a_usage_error(self) -> None:
        entry_id = self.create()
        with self.assertRaises(SystemExit) as caught:
            self.cli("update", entry_id, "--status", "done")
        self.assertEqual(caught.exception.code, 2)

    # -- check -------------------------------------------------------------

    def test_check_clean(self) -> None:
        self.create(
            "--tags", "python", "--status", "published", "--repository", "https://example.org/r"
        )
        code, out, _ = self.cli("check")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("0 error(s)", out)

    def test_check_detects_problems(self) -> None:
        bad = self.root / "content" / "technology" / "computer-science" / "projects" / "bad.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("no front matter", encoding="utf-8")
        code, out, _ = self.cli("check")
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("E001", out)

    def test_check_json(self) -> None:
        self.create()
        code, out, _ = self.cli("check", "--json")
        payload = json.loads(out)
        self.assertEqual(payload["checked"], 1)
        self.assertTrue(payload["ok"])

    def test_check_strict_fails_on_warning(self) -> None:
        self.create()  # no tags, draft: creates a warning
        code, _, _ = self.cli("check", "--strict")
        self.assertEqual(code, EXIT_ERROR)

    # -- stats -------------------------------------------------------------

    def test_stats_text_and_json(self) -> None:
        self.create()
        code, out, _ = self.cli("stats")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Portfolio: 1 entries", out)

        code, out, _ = self.cli("stats", "--json")
        self.assertEqual(json.loads(out)["total"], 1)

    def test_stats_write(self) -> None:
        self.create()
        code, out, _ = self.cli("stats", "--write")
        self.assertEqual(code, EXIT_OK)
        self.assertTrue((self.root / "data" / "portfolio_stats.json").is_file())

        target = self.sandbox.directory / "custom.json"
        code, out, _ = self.cli("stats", "--output", str(target))
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(target.is_file())

    # -- index / hugo ------------------------------------------------------

    def test_index(self) -> None:
        self.create()
        code, out, _ = self.cli("index")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("content/_index.md", out)
        self.assertTrue((self.root / "content" / "_index.md").is_file())

    def test_index_dry_run(self) -> None:
        self.create()
        code, out, _ = self.cli("index", "--dry-run", "--no-drafts", "--hugo-links")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Would write", out)
        self.assertFalse((self.root / "content" / "_index.md").exists())

    def test_hugo_apply(self) -> None:
        entry_id = self.create()
        text = (self.root / entry_id).read_text(encoding="utf-8")
        (self.root / entry_id).write_text(
            text.replace("draft: true", "draft: false"), encoding="utf-8"
        )
        code, out, _ = self.cli("hugo", "--apply")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Normalised 1 entry(ies)", out)
        self.assertIn("draft: true", (self.root / entry_id).read_text(encoding="utf-8"))

    def test_hugo_json(self) -> None:
        self.create("--status", "published", "--repository", "https://example.org/r")
        code, out, _ = self.cli("hugo", "--json")
        self.assertEqual(code, EXIT_OK, out)
        self.assertTrue(json.loads(out)["ok"])

    # -- error handling ----------------------------------------------------

    def test_missing_configuration(self) -> None:
        with patch("pfm.config.find_config_path", return_value=None):
            code = main(["list"])
        self.assertEqual(code, EXIT_ERROR)

    def test_unknown_command_is_a_usage_error(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            build_parser().parse_args(["frobnicate"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
