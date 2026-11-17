"""Tests for :mod:`pfm.config`."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pfm.config import find_config_path, load_config
from pfm.errors import ConfigError, ValidationError


class LoadConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.portfolio = self.directory / "portfolio"
        (self.portfolio / "content").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, payload: object, name: str = "config.json") -> Path:
        path = self.directory / name
        path.write_text(
            payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8"
        )
        return path

    def test_resolves_relative_root_from_config_location(self) -> None:
        config = load_config(self.write({"portfolio_root": "portfolio"}))
        self.assertEqual(config.portfolio_root, self.portfolio.resolve())
        self.assertEqual(config.content_root, self.portfolio.resolve() / "content")

    def test_preserves_absolute_root(self) -> None:
        config = load_config(self.write({"portfolio_root": str(self.portfolio)}))
        self.assertEqual(config.portfolio_root, self.portfolio.resolve())

    def test_missing_file(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.directory / "nope.json")

    def test_empty_file(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.write(""))

    def test_invalid_json(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.write("{not json"))

    def test_non_object(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.write([]))

    def test_missing_root_key(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.write({"domains": {}}))

    def test_non_string_root(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.write({"portfolio_root": 42}))

    def test_root_does_not_exist(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.write({"portfolio_root": "missing"}))

    def test_root_is_a_file(self) -> None:
        target = self.directory / "file.txt"
        target.write_text("x", encoding="utf-8")
        with self.assertRaises(ConfigError):
            load_config(self.write({"portfolio_root": "file.txt"}))

    def test_override_root(self) -> None:
        other = self.directory / "other"
        other.mkdir()
        config = load_config(self.write({"portfolio_root": "portfolio"}), portfolio_root=other)
        self.assertEqual(config.portfolio_root, other.resolve())

    def test_override_root_must_exist(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(
                self.write({"portfolio_root": "portfolio"}),
                portfolio_root=self.directory / "missing",
            )

    def test_custom_domains(self) -> None:
        config = load_config(
            self.write(
                {
                    "portfolio_root": "portfolio",
                    "domains": {"writing": ["essays"], "code": ["python"]},
                }
            )
        )
        self.assertEqual(config.domains, {"writing": ["essays"], "code": ["python"]})

    def test_invalid_domains(self) -> None:
        for bad in ({"a": []}, {"a": "b"}, {"": ["x"]}, [], {"a": [1]}):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                load_config(self.write({"portfolio_root": "portfolio", "domains": bad}))

    def test_default_tags(self) -> None:
        config = load_config(self.write({"portfolio_root": "portfolio", "default_tags": ["tech"]}))
        self.assertEqual(config.default_tags, ["tech"])

    def test_invalid_default_tags(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.write({"portfolio_root": "portfolio", "default_tags": "tech"}))

    def test_validate_domain_and_subdomain(self) -> None:
        config = load_config(self.write({"portfolio_root": "portfolio"}))
        self.assertIn("computer-science", config.validate_domain("technology"))
        with self.assertRaises(ValidationError):
            config.validate_domain("unknown")
        config.validate_subdomain("technology", "computer-science")
        with self.assertRaises(ValidationError):
            config.validate_subdomain("technology", "sociology")

    def test_to_dict(self) -> None:
        config = load_config(self.write({"portfolio_root": "portfolio"}))
        payload = config.to_dict()
        self.assertEqual(payload["portfolio_root"], str(self.portfolio.resolve()))
        self.assertIn("technology", payload["domains"])


class FindConfigPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.config_path = self.directory / "custom.json"
        self.config_path.write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_explicit_path_wins(self) -> None:
        self.assertEqual(find_config_path(self.config_path), self.config_path.resolve())

    def test_environment_variable(self) -> None:
        with patch.dict(os.environ, {"PFM_CONFIG": str(self.config_path)}):
            self.assertEqual(find_config_path(), self.config_path.resolve())

    def test_returns_none_when_nothing_found(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("pfm.config.Path.cwd", return_value=self.directory / "empty"):
                with patch("pfm.config.CONFIG_FILENAME", "definitely-missing.json"):
                    self.assertIsNone(find_config_path())


if __name__ == "__main__":
    unittest.main()
