-- Optional migration: no sample offers, approvals or grants are created.
-- Apply through the database owner's usual migration process.
CREATE TABLE IF NOT EXISTS retail.clearance_promotions (
    promotion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES retail.products(product_id),
    sale_price NUMERIC(10,2) NOT NULL CHECK (sale_price >= 0),
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL CHECK (ends_at > starts_at),
    approved_at TIMESTAMPTZ,
    approved_by TEXT,
    revoked_at TIMESTAMPTZ,
    CHECK ((approved_at IS NULL) = (approved_by IS NULL))
);
CREATE INDEX IF NOT EXISTS clearance_promotions_product_idx
    ON retail.clearance_promotions(product_id);
