import json
import os
import tempfile
import unittest
from pathlib import Path

from portfolio_manager import load_config


class LoadConfigTests(unittest.TestCase):
    def write_config(self, root, value):
        config_dir = root / "configs" / "nested"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps(value), encoding="utf-8")
        return config_path

    def test_resolves_portfolio_root_relative_to_config_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            portfolio_dir = root / "portfolio"
            (portfolio_dir / "content").mkdir(parents=True)
            config_path = self.write_config(root, {"portfolio_root": "../../portfolio"})

            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                config = load_config(config_path)
            finally:
                os.chdir(old_cwd)

            self.assertEqual(config["portfolio_root"], portfolio_dir.resolve())

    def test_preserves_absolute_portfolio_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            portfolio_dir = root / "portfolio"
            (portfolio_dir / "content").mkdir(parents=True)
            config_path = self.write_config(
                root, {"portfolio_root": str(portfolio_dir)}
            )

            config = load_config(config_path)

            self.assertEqual(config["portfolio_root"], portfolio_dir.resolve())

    def test_rejects_non_object_configuration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(Path(temp_dir), [])

            self.assertIsNone(load_config(config_path))

    def test_rejects_non_string_portfolio_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self.write_config(Path(temp_dir), {"portfolio_root": 42})

            self.assertIsNone(load_config(config_path))


if __name__ == "__main__":
    unittest.main()
