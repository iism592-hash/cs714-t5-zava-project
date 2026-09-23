#!/usr/bin/env python3
"""Backward-compatible launcher for the sales analysis MCP server."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SALES_DIR = ROOT / "sales_analysis"
if str(SALES_DIR) not in sys.path:
    sys.path.insert(0, str(SALES_DIR))

from sales_analysis import main  # noqa: E402


if __name__ == "__main__":
    main()
