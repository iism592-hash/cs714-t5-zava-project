-- Apply after clearance_promotions.sql. Recommendations are not public offers.
CREATE TABLE IF NOT EXISTS retail.inventory_scan_runs (
    scan_day DATE PRIMARY KEY,
    timezone TEXT NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    warning_count INTEGER NOT NULL,
    latest_order_date DATE
);
CREATE TABLE IF NOT EXISTS retail.promotion_recommendations (
    recommendation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scan_day DATE NOT NULL REFERENCES retail.inventory_scan_runs(scan_day),
    product_id INTEGER NOT NULL REFERENCES retail.products(product_id),
    warning_type TEXT NOT NULL CHECK (warning_type IN ('overstock', 'low_stock')),
    stock_level BIGINT NOT NULL,
    sold_30_days BIGINT NOT NULL,
    suggested_discount INTEGER NOT NULL CHECK (suggested_discount BETWEEN 0 AND 20),
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','revoked')),
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    UNIQUE(scan_day, product_id)
);
ALTER TABLE retail.clearance_promotions ADD COLUMN IF NOT EXISTS recommendation_id BIGINT
    REFERENCES retail.promotion_recommendations(recommendation_id);
CREATE UNIQUE INDEX IF NOT EXISTS clearance_recommendation_idx
    ON retail.clearance_promotions(recommendation_id) WHERE recommendation_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS retail.promotion_decisions (
    decision_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recommendation_id BIGINT NOT NULL REFERENCES retail.promotion_recommendations(recommendation_id),
    action TEXT NOT NULL CHECK (action IN ('approved','rejected','revoked')),
    actor TEXT NOT NULL,
    discount_percent INTEGER,
    reason TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
