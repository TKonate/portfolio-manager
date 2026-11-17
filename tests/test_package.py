"""Packaging sanity checks: version, assets and the backward compatible entry point."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import pfm
from pfm import cli


class PackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parent.parent

    def test_version_is_semver(self) -> None:
        self.assertRegex(pfm.__version__, r"^\d+\.\d+\.\d+$")

    def test_version_matches_pyproject(self) -> None:
        text = (self.repo / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), pfm.__version__)

    def test_console_scripts_exist(self) -> None:
        text = (self.repo / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('pfm = "pfm.cli:main"', text)
        self.assertIn('portfolio-manager = "pfm.cli:main"', text)

    def test_web_assets_are_packaged(self) -> None:
        web = Path(pfm.__file__).parent / "web"
        for asset in ("index.html", "app.js", "style.css"):
            self.assertTrue((web / asset).is_file(), asset)
        text = (self.repo / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('pfm = ["web/*"]', text)

    def test_legacy_entry_point_imports_main(self) -> None:
        text = (self.repo / "portfolio_manager.py").read_text(encoding="utf-8")
        self.assertIn("from pfm.cli import main", text)
        self.assertEqual(cli.main.__module__, "pfm.cli")

    def test_module_entry_point(self) -> None:
        self.assertTrue((Path(pfm.__file__).parent / "__main__.py").is_file())

    def test_license_and_readme_exist(self) -> None:
        self.assertTrue((self.repo / "LICENSE").is_file())
        self.assertTrue((self.repo / "README.md").is_file())
        self.assertTrue((self.repo / "ROADMAP.md").is_file())


if __name__ == "__main__":
    unittest.main()
