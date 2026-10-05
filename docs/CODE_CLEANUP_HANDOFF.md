# Code cleanup handoff

This branch addresses catalog/cart integrity and repository hygiene. It does not deploy Azure changes.

## Behavior changes
- Resolve recommendation link text by exact normalized catalog name. Do not substitute loosely related products or manufacture product IDs, SKUs, or prices.
- Report partial bundles with unavailable names. Await async resolution before announcing success. Ignore overlapping bulk-add operations.
- Root requirements.txt delegates to src/python/requirements.txt, the Docker dependency source.
- start.sh monitors all three B2C child processes, cleans up on signals/exit, and polls web /health during startup. B2B keeps its exec launch.
- Local root diagnostic/migration scripts and SQL were moved to ignored scripts/local-diagnostics/. Ad hoc root tests were moved to ignored tests/diagnostics/. These may contain environment-specific settings; they are intentionally not published. Run them from the repository root if they depend on relative paths.
- Deployment ZIPs, extracted logs, appsettings.json and temporary extraction directories are ignored, retained locally.

## Validation
node --check src/shared/static/chat.js
node tests/cart_bundle.test.cjs

The test covers exact matching despite misleading search results, missing recommendations and catalog request failure. Bash/WSL syntax check could not run because this Windows host has no Linux /bin/bash. Container service supervision and startup readiness need Linux validation before deployment.

## Existing work and follow-up
The working checkout already contained substantial deployment/backend edits and deletion of vendored agent_framework. Those unrelated edits/deletions are left uncommitted. The committed chat.js includes the pre-existing cart UI work necessary for the new behavior. Do not blindly stage the remaining working tree.
Missing catalog items are now unavailable, rather than invented. Add real PPE products to the database if the project needs them. Exact matching intentionally rejects aliases; a future API should provide stable product IDs in structured AI recommendations.
