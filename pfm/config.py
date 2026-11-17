"""Configuration loading and validation.

The configuration file is a small JSON document::

    {
      "portfolio_root": "../portfolio",
      "domains": {
        "technology": ["computer-science", "electronics"]
      }
    }

Only ``portfolio_root`` is mandatory.  Relative paths are resolved from the
directory that contains the configuration file, never from the current working
directory, so the tool behaves the same whatever the shell location.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigError
from .models import DEFAULT_DOMAINS

#: Environment variable pointing to an alternative configuration file.
CONFIG_ENV_VAR = "PFM_CONFIG"

#: Name of the configuration file.
CONFIG_FILENAME = "config.json"


@dataclass
class Config:
    """Resolved configuration.

    Attributes:
        portfolio_root: Absolute path to the portfolio (parent of ``content/``).
        domains: Allowed domain -> subdomain mapping.
        default_tags: Tags suggested (and applied by default) on creation.
        config_path: Absolute path of the file the configuration came from.
    """

    portfolio_root: Path
    config_path: Path
    domains: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_DOMAINS))
    default_tags: list[str] = field(default_factory=list)

    @property
    def content_root(self) -> Path:
        """Absolute path of the ``content/`` directory."""
        return self.portfolio_root / "content"

    @property
    def data_root(self) -> Path:
        """Absolute path of the generated ``data/`` directory."""
        return self.portfolio_root / "data"

    def subdomains(self, domain: str) -> list[str]:
        """Subdomains declared for ``domain`` (empty when unknown)."""
        return list(self.domains.get(domain, []))

    def validate_domain(self, domain: str) -> list[str]:
        """Validate a domain name and return its subdomains.

        Raises:
            ValidationError: Imported lazily to avoid a circular import.
        """
        from .errors import ValidationError

        if domain not in self.domains:
            allowed = ", ".join(sorted(self.domains)) or "(none configured)"
            raise ValidationError(
                f"unknown domain: {domain!r}",
                [f"allowed domains: {allowed}"],
            )
        return list(self.domains[domain])

    def validate_subdomain(self, domain: str, subdomain: str) -> None:
        """Validate ``subdomain`` against the configured tree."""
        from .errors import ValidationError

        allowed = self.validate_domain(domain)
        if subdomain not in allowed:
            raise ValidationError(
                f"invalid subdomain for {domain!r}: {subdomain!r}",
                [f"allowed subdomains: {', '.join(allowed) or '(none configured)'}"],
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the configuration (used by the web UI bootstrap)."""
        return {
            "portfolio_root": str(self.portfolio_root),
            "domains": {key: list(value) for key, value in self.domains.items()},
            "default_tags": list(self.default_tags),
        }


def find_config_path(explicit: str | Path | None = None) -> Path | None:
    """Locate the configuration file.

    Resolution order: explicit argument, ``$PFM_CONFIG``, current directory,
    then the repository root (useful when the tool is installed with pip and
    launched from elsewhere).

    An explicit path -- the ``--config`` flag or ``$PFM_CONFIG`` -- must exist:
    silently falling back to another file would hide a typo and read the wrong
    portfolio.

    Raises:
        ConfigError: When an explicitly requested file does not exist.
    """
    if explicit is not None:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return candidate.resolve()
        raise ConfigError(f"configuration file not found: {candidate}")

    env_value = os.environ.get(CONFIG_ENV_VAR)
    if env_value:
        candidate = Path(env_value).expanduser()
        if candidate.is_file():
            return candidate.resolve()
        raise ConfigError(f"{CONFIG_ENV_VAR} points to a missing file: {candidate}")

    for candidate in (
        Path.cwd() / CONFIG_FILENAME,
        Path(__file__).resolve().parent.parent / CONFIG_FILENAME,
    ):
        if candidate.is_file():
            return candidate.resolve()
    return None


def _parse_domains(raw: Any) -> dict[str, list[str]]:
    """Validate the optional ``domains`` section."""
    if raw is None:
        return dict(DEFAULT_DOMAINS)
    if not isinstance(raw, dict):
        raise ConfigError('"domains" must be an object mapping domain -> list of subdomains')

    domains: dict[str, list[str]] = {}
    for domain, subdomains in raw.items():
        if not isinstance(domain, str) or not domain.strip():
            raise ConfigError('"domains" keys must be non-empty strings')
        if not isinstance(subdomains, list) or not subdomains:
            raise ConfigError(f'"domains.{domain}" must be a non-empty list')
        cleaned: list[str] = []
        for subdomain in subdomains:
            if not isinstance(subdomain, str) or not subdomain.strip():
                raise ConfigError(f'"domains.{domain}" entries must be non-empty strings')
            cleaned.append(subdomain.strip())
        domains[domain.strip()] = cleaned
    if not domains:
        raise ConfigError('"domains" cannot be empty')
    return domains


def load_config(
    config_path: str | Path | None = None,
    *,
    portfolio_root: str | Path | None = None,
) -> Config:
    """Load, validate and resolve the configuration.

    Args:
        config_path: Optional explicit path to ``config.json``.
        portfolio_root: Optional override of ``portfolio_root`` (CLI flag).  The
            path is resolved from the current working directory and must exist.

    Raises:
        ConfigError: When the file is missing, empty, not valid JSON, or when a
            field has the wrong type or points to a non-existent directory.
    """
    path = find_config_path(config_path)
    if path is None:
        raise ConfigError(
            "config.json not found. Create one with:\n"
            '  { "portfolio_root": "../portfolio" }\n'
            "or pass --config /path/to/config.json."
        )

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - unreadable file is rare
        raise ConfigError(f"cannot read {path}: {exc}") from exc

    if not raw_text.strip():
        raise ConfigError(f"{path} is empty")

    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a JSON object")

    root_value = raw.get("portfolio_root")
    if root_value is None:
        raise ConfigError(f'"portfolio_root" is missing from {path}')
    if not isinstance(root_value, str) or not root_value.strip():
        raise ConfigError('"portfolio_root" must be a non-empty string')

    if portfolio_root is not None:
        root = Path(portfolio_root).expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root
    else:
        root = Path(root_value).expanduser()
        if not root.is_absolute():
            # Relative to the configuration file, not to the current directory.
            root = path.parent / root
    root = root.resolve()

    if not root.exists():
        raise ConfigError(f"portfolio root does not exist: {root}")
    if not root.is_dir():
        raise ConfigError(f"portfolio root is not a directory: {root}")

    default_tags_raw = raw.get("default_tags", [])
    if not isinstance(default_tags_raw, list) or any(
        not isinstance(tag, str) for tag in default_tags_raw
    ):
        raise ConfigError('"default_tags" must be a list of strings')

    return Config(
        portfolio_root=root,
        config_path=path,
        domains=_parse_domains(raw.get("domains")),
        default_tags=[tag.strip() for tag in default_tags_raw if tag.strip()],
    )
