# Inventory warning → manager review → B2C offer

The B2B process checks every day at 08:00 America/Los_Angeles, with automatic
daylight-saving adjustment. App Service Always On keeps the worker available.
If restarted after the scheduled time, it catches up; a PostgreSQL advisory lock
and unique scan date prevent duplicate runs across restarts or instances.
Failures retry in 60 seconds. Check inventory now refreshes pending warnings
without overwriting existing manager decisions.
The B2B warning pane refreshes every 60 seconds while the page is open, so a new
morning scan is visible without manually reloading. AI explanations are retained
in the signed-in session across these refreshes.

Rules use current aggregate stock and units sold during the preceding 30 days,
ending on the scan date. Low stock is ≤10 units or <7 days of cover. Overstock
is ≥100 units with no recent sales, or ≥90 days of cover. Recommendations suggest
10%, or 20% for ≥180 days of cover, bounded by a 20% discount cap and minimum
10% gross margin. Low stock recommends replenishment, not promotion. The dashboard
shows the latest recorded sale and warns about stale sales data. Rules are
explicit; the optional AI explanation cannot write or approve prices.

Manager review requires a username and salted scrypt password hash configured in
B2B App Service settings. The generated initial login is stored only in ignored
`scripts/local-diagnostics/promotion-manager.credentials.json`; it is not in Git,
container images or B2C settings. Sessions expire after an hour. Decision reasons
are required; the authenticated manager identity is recorded with every action.
The existing analyst chat remains separate from the protected review controls.
Its SQL tool executes inside a read-only PostgreSQL transaction, so neither chat
nor the AI explanation can bypass the review controls to write promotion tables.

Approval locks the pending recommendation, rechecks current product price/cost,
validates a 1–30 day duration and discount/margin bounds, writes the offer and
audit entry atomically. Repeated approval is rejected. Rejection creates no offer.
Revocation removes that offer from B2C immediately on its next catalog request;
expiration is enforced in database queries. Historical decisions are retained.

B2C's clearance endpoint, regular catalog and AI product lookup receive the same
eligible sale prices. Product cards show original/sale prices, and the estimated
cart uses the sale price. Checkout is still a browser estimate; a future actual
purchase service must revalidate stock and promotion validity when placing orders.

Database setup: apply `clearance_promotions.sql` followed by
`inventory_promotions.sql`. `scripts/setup_inventory_promotions.py` performs the
migration transactionally and grants B2C read-only offer access and B2B workflow
permissions. It never creates or approves offers. The administrator connection
must be supplied securely through environment variables. The worker app identity
does not receive schema-administration privileges.

Tests: `tests/inventory_promotion_workflow.py` exercises real local PostgreSQL and
the B2C endpoint with rollback fixtures; `tests/promotion_login_ui.py` verifies
Streamlit login gating and low-stock controls. Existing cart regression checks
remain in `tests/clearance_cart.test.cjs` and `tests/cart_bundle.test.cjs`.

Deployment overlays the modified workflow files onto the immutable previous live
image; unrelated local infrastructure/backend work is not included. Production
scans may create pending recommendations. Testing does not approve actual offers.

## Live verification — 7 October 2026 (Europe/London)

Implementation commits `225494f`, `c07776f` and `f614144` are pushed; draft
PR #1 is stacked on the clearance branch. B2B runs `inventory-workflow-final-2`
(digest `sha256:ba17f89ea87249cc54db560de725404665629918e6de33d0c292e0d75a558263`);
B2C runs `inventory-workflow-3`
(digest `sha256:603f2471b2f8851cd79216228e5137aa83510fa6ac1e59cbc872b08cfcaecf9f`).

An authenticated live scan generated 424 pending warnings; restart preserved them.
Live AI explanation completed and clearance remained empty (no approved offers).
The B2B warning pane refreshes every 60 seconds while open, shows pending-review
counts and retains the selected recommendation's AI explanation across refreshes.
Azure migration succeeded from a disposable internal container, which was removed.
B2B and B2C health checks returned 200 after container warmup recovered.

All local workflow, login, read-only SQL and cart tests passed. Approval mutations
used rollback fixtures only; actual future 08:00 execution was not awaited.
The 90-day cover rule also applies below 100 units when recent sales are positive;
the 100-unit floor is only for zero recent sales. The 50-stock/5-sales case and
full workflow integration passed. Streamlit login/control tests passed with the
final fragment refresh enabled.
