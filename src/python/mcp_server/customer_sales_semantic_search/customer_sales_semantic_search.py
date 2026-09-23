#!/usr/bin/env python3
"""Legacy compatibility wrapper for the semantic customer sales MCP server."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUSTOMER_DIR = ROOT / "customer_sales"
if str(CUSTOMER_DIR) not in sys.path:
    sys.path.insert(0, str(CUSTOMER_DIR))

from customer_sales_semantic_search import main  # noqa: E402


if __name__ == "__main__":
    main()
