"""Read approved clearance offers without inventing discounts or modifying data."""
import logging
from fastapi import HTTPException, Query


def install_clearance_routes(web_app):
    @web_app.app.get('/api/clearance')
    async def clearance_products(
        category: str | None = None, search: str | None = None,
        limit: int = Query(24, ge=1, le=100), offset: int = Query(0, ge=0),
    ):
        conn = None
        try:
            if hasattr(web_app, '_get_db_connection'):
                conn = await web_app._get_db_connection()
            else:
                import asyncpg
                conn = await asyncpg.connect(web_app.postgres_url)
            await conn.execute("SELECT set_config('app.current_rls_user_id', $1, false)", web_app.rls_user_id)
            if not await conn.fetchval("SELECT to_regclass('retail.clearance_promotions')"):
                return {'products': [], 'count': 0, 'limit': limit, 'offset': offset}
            rows = await conn.fetch("""
                SELECT p.product_id, p.sku, p.product_name, p.product_description,
                       p.base_price::float AS base_price,
                       offer.sale_price::float AS sale_price,
                       offer.ends_at AS promotion_ends_at,
                       c.category_name, pt.type_name,
                       COALESCE((SELECT image_url FROM retail.product_image_embeddings
                                 WHERE product_id=p.product_id LIMIT 1), '') AS image_url,
                       COALESCE((SELECT SUM(stock_level) FROM retail.inventory
                                 WHERE product_id=p.product_id), 0) AS total_stock
                FROM retail.products p
                JOIN retail.categories c USING (category_id)
                JOIN retail.product_types pt USING (type_id)
                JOIN LATERAL (
                    SELECT sale_price, ends_at FROM retail.clearance_promotions
                    WHERE product_id=p.product_id AND approved_at IS NOT NULL
                      AND approved_by IS NOT NULL AND revoked_at IS NULL
                      AND starts_at <= CURRENT_TIMESTAMP AND ends_at > CURRENT_TIMESTAMP
                      AND sale_price >= 0 AND sale_price < p.base_price
                    ORDER BY sale_price, ends_at DESC LIMIT 1
                ) offer ON TRUE
                WHERE ($1::text IS NULL OR c.category_name ILIKE $1)
                  AND ($2::text IS NULL OR p.product_name ILIKE $2 OR p.sku ILIKE $2)
                ORDER BY p.product_name, p.product_id LIMIT $3 OFFSET $4
            """, f'%{category}%' if category and category != 'All' else None,
                f'%{search.strip()}%' if search and search.strip() else None, limit, offset)
            return {'products': [dict(r) for r in rows], 'count': len(rows), 'limit': limit, 'offset': offset}
        except Exception as exc:
            logging.exception('Clearance catalog query failed')
            raise HTTPException(503, 'Clearance offers could not be loaded. Please try again.') from exc
        finally:
            if conn is not None:
                await conn.close()
