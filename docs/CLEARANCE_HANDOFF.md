# Clearance catalog

Shop Clearance now requests `/api/clearance`; it does not relabel the full catalog.
Only approved, unrevoked offers within their validity period and below the original
catalog price qualify. Missing promotion schema yields an empty catalog; database
errors return 503 and are displayed as errors rather than as empty offers.

`data/database/clearance_promotions.sql` is an optional, data-free migration.
Apply it using the database owner's normal migration process and grant SELECT to
the storefront role. No production offers, approvals, or permissions were created
by this change. The banner no longer claims an unverified 20% discount.

Sale cards show both prices and the cart uses the displayed sale price, including
zero-priced offers. Adding the same SKU updates the existing line price. All
Products/category buttons leave the clearance view; searching/pagination retain
it. This project currently provides an estimated browser cart, not a server-side
checkout. Checkout must revalidate offers when a purchasing service is implemented.

The web-app installation hook is the only change to the existing backend file;
unrelated local backend work remains outside this commit. Existing banner/cart
HTML is included because the current frontend requires those elements.

## Live verification (6 October 2026)

Deployed `zavaacrfntj.azurecr.io/zava-agent:clearance-2`, digest
`sha256:61b0d665a04959e57e20747424a022f28b3afe11e0a3d7720c6de520d9ddabbb`.
Live `/api/clearance` returned HTTP 200 with no offers; the button displayed the
empty clearance state, and All Products restored 24 normal catalog items.
Both web and agent health checks passed after warmup. Several initial requests
timed out during startup, then recovered. No live discounted item was tested
because no production offers were created. Local SQL and cart-price tests passed.
The branch was pushed; PR creation through the GitHub connector returned HTTP 403.
