"""Shared test helpers: temporary portfolios and CLI runners."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from pfm.cli import main
from pfm.config import Config, load_config
from pfm.models import DEFAULT_DOMAINS

CONFIG_TEMPLATE: dict[str, Any] = {"portfolio_root": "portfolio"}


@dataclass
class Sandbox:
    """A temporary portfolio plus the configuration that points at it."""

    directory: Path
    root: Path
    config_path: Path
    config: Config


def make_sandbox(**config_overrides: Any) -> tuple[TemporaryDirectory[str], Sandbox]:
    """Create a temporary portfolio on disk.

    Returns the ``TemporaryDirectory`` object (keep a reference so it is not
    garbage collected) and a :class:`Sandbox`.
    """
    temp = TemporaryDirectory()
    directory = Path(temp.name)
    root = directory / "portfolio"
    (root / "content").mkdir(parents=True)
    data: dict[str, Any] = {**CONFIG_TEMPLATE, **config_overrides}
    config_path = directory / "config.json"
    config_path.write_text(json.dumps(data), encoding="utf-8")
    config = load_config(config_path)
    return temp, Sandbox(directory=directory, root=root, config_path=config_path, config=config)


def make_config(root: Path) -> Config:
    """Build a :class:`Config` directly, without touching the filesystem."""
    return Config(
        portfolio_root=root,
        config_path=root / "config.json",
        domains=dict(DEFAULT_DOMAINS),
    )


def run_cli(args: list[str], config_path: Path) -> tuple[int, str, str]:
    """Run the CLI in-process and capture ``(exit_code, stdout, stderr)``."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(["--config", str(config_path), *args])
    return code, stdout.getvalue(), stderr.getvalue()


def read_document(path: Path) -> str:
    """Read a file as UTF-8 text."""
    return path.read_text(encoding="utf-8")
