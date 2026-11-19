"""Package root of Portfolio Manager.

The package is a library first: ``pfm.cli`` and ``pfm.server`` are entry points
that build on it, while every other module stays ignorant of the terminal and
of HTTP.

Only the version is exported here.  This module is imported by ``pfm.stats`` to
stamp the JSON it writes, so it must stay free of side effects and cheap to
import: no argument parsing, no filesystem access, no server.
"""

from __future__ import annotations

__version__ = "1.0.1"

__all__ = ["__version__"]
