#!/usr/bin/env python3
"""Backward compatible entry point.

Historically the tool was a single script called with::

    python portfolio_manager.py new publication

That command must keep working, so this file only forwards to
:func:`pfm.cli.main`.  New code, and the installed ``portfolio-manager`` /
``pfm`` console scripts, call the package directly.
"""

from __future__ import annotations

from pfm.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
