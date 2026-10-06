from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from .db import connect


def recommend(stock, sold, base_price, cost):
    """Transparent rules; no unsupported competitor or demand claims."""
    stock, sold = int(stock), int(sold)
    days = stock * 30 / sold if sold > 0 else None
    if stock <= 10 or (sold > 0 and days < 7):
        return 'low_stock', 0, f'Stock {stock}; last 30 days sold {sold}. Restock; no discount recommended.'
    if stock >= 100 and (sold == 0 or days >= 90):
        target = 10 if sold == 0 else (20 if days >= 180 else 10)
        maximum = max_discount(base_price, cost)
        discount = min(target, maximum)
        return 'overstock', discount, f'Stock {stock}; last 30 days sold {sold}. Excess stock; review a {discount}% offer. Minimum gross margin 10%.'
    return None


def max_discount(base_price, cost):
    base, cost = Decimal(str(base_price)), Decimal(str(cost))
    if base <= 0 or cost < 0:
        return 0
    # Whole-percent discounts; reserve at least 10% gross margin.
    return max(0, min(20, int((1 - cost / (base * Decimal('0.9'))) * 100)))


async def scan_inventory(scan_day: date, timezone: str, force=False):
    conn = await connect()
    try:
        async with conn.transaction():
            if not await conn.fetchval('SELECT pg_try_advisory_xact_lock(714716)'):
                return {'skipped': 'scan already running'}
            exists = await conn.fetchval('SELECT warning_count FROM retail.inventory_scan_runs WHERE scan_day=$1', scan_day)
            if exists is not None and not force:
                return {'skipped': 'already checked today', 'warning_count': exists}
            rows = await conn.fetch("""
                SELECT p.product_id, p.base_price, p.cost,
                  COALESCE((SELECT SUM(stock_level) FROM retail.inventory i WHERE i.product_id=p.product_id),0) AS stock,
                  COALESCE((SELECT SUM(oi.quantity) FROM retail.order_items oi
                    JOIN retail.orders o USING(order_id)
                    WHERE oi.product_id=p.product_id AND o.order_date > $1::date - 30
                      AND o.order_date <= $1::date),0) AS sold
                FROM retail.products p ORDER BY p.product_id
            """, scan_day)
            warnings = [(r, recommend(r['stock'], r['sold'], r['base_price'], r['cost'])) for r in rows]
            warnings = [(r, w) for r, w in warnings if w]
            latest = await conn.fetchval('SELECT MAX(order_date) FROM retail.orders WHERE order_date <= $1', scan_day)
            await conn.execute("""
                INSERT INTO retail.inventory_scan_runs(scan_day,timezone,warning_count,latest_order_date)
                VALUES($1,$2,$3,$4) ON CONFLICT(scan_day) DO UPDATE SET
                timezone=EXCLUDED.timezone, warning_count=EXCLUDED.warning_count,
                latest_order_date=EXCLUDED.latest_order_date, completed_at=CURRENT_TIMESTAMP
            """, scan_day, timezone, len(warnings), latest)
            for row, (kind, discount, reason) in warnings:
                await conn.execute("""
                    INSERT INTO retail.promotion_recommendations
                     (scan_day,product_id,warning_type,stock_level,sold_30_days,suggested_discount,reason)
                    VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT(scan_day,product_id) DO UPDATE SET
                    stock_level=EXCLUDED.stock_level,sold_30_days=EXCLUDED.sold_30_days,
                    suggested_discount=EXCLUDED.suggested_discount,reason=EXCLUDED.reason,
                    warning_type=EXCLUDED.warning_type
                    WHERE retail.promotion_recommendations.status='pending'
                """, scan_day, row['product_id'], kind, row['stock'], row['sold'], discount, reason)
            # Pending warnings resolved by a refreshed scan must not stay actionable.
            ids = [r['product_id'] for r, _ in warnings]
            await conn.execute("""DELETE FROM retail.promotion_recommendations
                WHERE scan_day=$1 AND status='pending' AND NOT (product_id=ANY($2::int[]))""", scan_day, ids)
            return {'warning_count': len(warnings), 'latest_order_date': str(latest)}
    finally:
        await conn.close()


async def dashboard():
    conn = await connect()
    try:
        run = await conn.fetchrow('SELECT * FROM retail.inventory_scan_runs ORDER BY scan_day DESC LIMIT 1')
        rows = await conn.fetch("""
            SELECT r.*, p.product_name, p.sku, p.base_price, p.cost,
              cp.sale_price, cp.ends_at, cp.promotion_id
            FROM retail.promotion_recommendations r JOIN retail.products p USING(product_id)
            LEFT JOIN retail.clearance_promotions cp USING(recommendation_id)
            WHERE r.scan_day=(SELECT MAX(scan_day) FROM retail.inventory_scan_runs)
               OR (r.status='approved' AND cp.ends_at>CURRENT_TIMESTAMP AND cp.revoked_at IS NULL)
            ORDER BY r.status, r.warning_type DESC, r.stock_level DESC, r.recommendation_id
        """)
        return dict(run) if run else None, [dict(r) for r in rows]
    finally:
        await conn.close()


async def decide(recommendation_id, action, actor, discount=0, days=7, reason=''):
    if action not in ('approved', 'rejected', 'revoked') or not actor or not reason.strip():
        raise ValueError('A manager identity and decision reason are required.')
    conn = await connect()
    try:
        async with conn.transaction():
            row = await conn.fetchrow("""SELECT r.*,p.base_price,p.cost FROM retail.promotion_recommendations r
                JOIN retail.products p USING(product_id) WHERE recommendation_id=$1 FOR UPDATE OF r""", recommendation_id)
            if not row:
                raise ValueError('Recommendation no longer exists. Refresh the dashboard.')
            if action == 'revoked':
                if row['status'] != 'approved':
                    raise ValueError('Only an approved offer can be revoked.')
                await conn.execute('UPDATE retail.clearance_promotions SET revoked_at=CURRENT_TIMESTAMP WHERE recommendation_id=$1', recommendation_id)
            else:
                if row['status'] != 'pending':
                    raise ValueError('This recommendation has already been reviewed.')
                if action == 'approved':
                    from zoneinfo import ZoneInfo
                    from datetime import datetime
                    import os
                    today = datetime.now(ZoneInfo(os.getenv('INVENTORY_CHECK_TIMEZONE','America/Los_Angeles'))).date()
                    if row['scan_day'] != today:
                        raise ValueError('Run a fresh inventory check before approving an old recommendation.')
                    if row['warning_type'] != 'overstock' or not 1 <= discount <= max_discount(row['base_price'], row['cost']) or not 1 <= days <= 30:
                        raise ValueError('Discount must fit the 20% cap and minimum 10% gross margin; duration must be 1–30 days.')
                    sale = (row['base_price'] * (Decimal(100)-Decimal(discount))/100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    if sale <= 0 or sale * Decimal('0.9') < row['cost']:
                        raise ValueError('Rounded sale price would violate the minimum gross margin.')
                    await conn.execute("""INSERT INTO retail.clearance_promotions
                        (product_id,sale_price,starts_at,ends_at,approved_at,approved_by,recommendation_id)
                        VALUES($1,$2,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP + $3 * INTERVAL '1 day',CURRENT_TIMESTAMP,$4,$5)""",
                        row['product_id'], sale, days, actor, recommendation_id)
            await conn.execute("""UPDATE retail.promotion_recommendations SET status=$2,
                reviewed_by=$3,reviewed_at=CURRENT_TIMESTAMP WHERE recommendation_id=$1""", recommendation_id, action, actor)
            await conn.execute("""INSERT INTO retail.promotion_decisions
                (recommendation_id,action,actor,discount_percent,reason) VALUES($1,$2,$3,$4,$5)""",
                recommendation_id, action, actor, discount if action=='approved' else None, reason.strip())
    finally:
        await conn.close()
