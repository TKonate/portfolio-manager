"""Exception hierarchy used across Portfolio Manager.

Keeping a dedicated hierarchy lets the CLI translate failures into clean
messages and exit codes instead of leaking tracebacks to the user.
"""

from __future__ import annotations


class PortfolioError(Exception):
    """Base class for every expected failure of the tool."""


class ConfigError(PortfolioError):
    """The configuration file is missing, malformed or points nowhere useful."""


class ValidationError(PortfolioError):
    """User supplied values (or a front matter block) are invalid.

    Attributes:
        message: Human readable explanation.
        details: Optional list of precise problems (one per field).
    """

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class EntryError(PortfolioError):
    """An entry cannot be read, parsed or written."""


class EntryNotFoundError(EntryError):
    """The requested entry does not exist inside the portfolio."""


class UnsafePathError(EntryError):
    """A path tried to escape the portfolio root."""
