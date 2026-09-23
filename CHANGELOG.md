# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Fixed

- Fixed stale MCP server startup configuration that caused `--port`/`--host` arguments to be rejected.
- Added compatibility support for HTTP mode arguments in the real server entry points for sales analysis and customer sales MCP servers.
- Added legacy launcher files to preserve compatibility with earlier repo paths and commands that referenced `mcp_server_sales_analysis.py` and top-level `customer_sales.py` / `sales_analysis.py` scripts.
- Restored compatibility for old launch patterns that expected direct script execution from the `src/python/mcp_server` folder.
- Verified the server CLIs now accept the expected arguments without raising `unrecognized arguments` errors.

### Notes

- The project dependencies in `src/python/requirements.txt` were installed to ensure the MCP servers could start in the local workspace environment.
