"""
deep_dive_02.py
Run deep exploratory queries to answer all questions from 02-analyse guide.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://store_manager:StoreManager123!@127.0.0.1:15432/zava")
SUPER_ADMIN_ID = "00000000-0000-0000-0000-000000000000"

async def deep_dive():
    conn = await asyncpg.connect(POSTGRES_URL)
    try:
        await conn.execute(f"SET app.current_rls_user_id = '{SUPER_ADMIN_ID}';")
    except Exception:
        pass

    print("=" * 70)
    print("1. YEAR OVER YEAR REVENUE & ORDERS (2020 - 2026)")
    print("=" * 70)
    rows = await conn.fetch("""
        SELECT 
            EXTRACT(YEAR FROM o.order_date)::int as yr,
            COUNT(DISTINCT o.order_id) as total_orders,
            ROUND(SUM(oi.unit_price * oi.quantity)::numeric, 2) as rev
        FROM retail.orders o
        JOIN retail.order_items oi ON o.order_id = oi.order_id
        GROUP BY yr ORDER BY yr;
    """)
    for r in rows:
        print(f"Year {r['yr']}: Orders={r['total_orders']:>7,}, Revenue=${r['rev']:>12,}")

    print("\n" + "=" * 70)
    print("2. 2023 DIP DEEP DIVE: MONTH-BY-MONTH (2022 vs 2023 vs 2024)")
    print("=" * 70)
    rows = await conn.fetch("""
        SELECT 
            EXTRACT(MONTH FROM o.order_date)::int as mo,
            ROUND(SUM(CASE WHEN EXTRACT(YEAR FROM o.order_date) = 2022 THEN oi.unit_price * oi.quantity ELSE 0 END)::numeric, 2) as rev_2022,
            ROUND(SUM(CASE WHEN EXTRACT(YEAR FROM o.order_date) = 2023 THEN oi.unit_price * oi.quantity ELSE 0 END)::numeric, 2) as rev_2023,
            ROUND(SUM(CASE WHEN EXTRACT(YEAR FROM o.order_date) = 2024 THEN oi.unit_price * oi.quantity ELSE 0 END)::numeric, 2) as rev_2024
        FROM retail.orders o
        JOIN retail.order_items oi ON o.order_id = oi.order_id
        WHERE EXTRACT(YEAR FROM o.order_date) IN (2022, 2023, 2024)
        GROUP BY mo ORDER BY mo;
    """)
    for r in rows:
        pct_change_22_23 = ((r['rev_2023'] - r['rev_2022']) / r['rev_2022'] * 100) if r['rev_2022'] else 0
        print(f"Month {r['mo']:>2}: 2022=${r['rev_2022']:>10,} | 2023=${r['rev_2023']:>10,} ({pct_change_22_23:>+6.1f}%) | 2024=${r['rev_2024']:>10,}")

    print("\n" + "=" * 70)
    print("3. CATEGORY SEASONALITY SWINGS (Min month vs Max month)")
    print("=" * 70)
    rows = await conn.fetch("""
        WITH monthly AS (
            SELECT 
                c.category_name,
                EXTRACT(MONTH FROM o.order_date)::int as mo,
                SUM(oi.quantity) as qty
            FROM retail.categories c
            JOIN retail.products p ON c.category_id = p.category_id
            JOIN retail.order_items oi ON p.product_id = oi.product_id
            JOIN retail.orders o ON oi.order_id = o.order_id
            GROUP BY c.category_name, mo
        )
        SELECT 
            category_name,
            MIN(qty) as min_qty,
            MAX(qty) as max_qty,
            ROUND((MAX(qty)::numeric / NULLIF(MIN(qty),0)), 2) as swing_ratio
        FROM monthly
        GROUP BY category_name
        ORDER BY swing_ratio DESC;
    """)
    for r in rows:
        print(f"{r['category_name']:<32} | Min={r['min_qty']:>6,} | Max={r['max_qty']:>6,} | Swing={r['swing_ratio']:>4}x")

    print("\n" + "=" * 70)
    print("4. TOP 5 PRODUCT CO-PURCHASE AFFINITIES (Market Basket)")
    print("=" * 70)
    rows = await conn.fetch("""
        SELECT 
            p1.product_name as prod1,
            p2.product_name as prod2,
            COUNT(*) as times_bought_together
        FROM retail.order_items oi1
        JOIN retail.order_items oi2 ON oi1.order_id = oi2.order_id AND oi1.product_id < oi2.product_id
        JOIN retail.products p1 ON oi1.product_id = p1.product_id
        JOIN retail.products p2 ON oi2.product_id = p2.product_id
        GROUP BY p1.product_name, p2.product_name
        ORDER BY times_bought_together DESC
        LIMIT 5;
    """)
    for r in rows:
        print(f"- {r['prod1']} + {r['prod2']}: {r['times_bought_together']} times")

    print("\n" + "=" * 70)
    print("5. INVENTORY VS SALES VELOCITY (Stockout vs Overstock Mismatch)")
    print("=" * 70)
    rows = await conn.fetch("""
        WITH sales AS (
            SELECT 
                oi.product_id,
                o.store_id,
                SUM(oi.quantity) as total_sold
            FROM retail.order_items oi
            JOIN retail.orders o ON oi.order_id = o.order_id
            GROUP BY oi.product_id, o.store_id
        )
        SELECT 
            s.store_name,
            p.product_name,
            COALESCE(i.stock_level, 0) as current_stock,
            COALESCE(sl.total_sold, 0) as historical_sales
        FROM retail.inventory i
        JOIN retail.stores s ON i.store_id = s.store_id
        JOIN retail.products p ON i.product_id = p.product_id
        LEFT JOIN sales sl ON i.product_id = sl.product_id AND i.store_id = sl.store_id
        ORDER BY current_stock ASC
        LIMIT 5;
    """)
    print("Lowest Stock Items across Stores:")
    for r in rows:
        print(f"Store: {r['store_name']:<18} | {r['product_name']:<35} | Stock: {r['current_stock']:>3} | Total Sold: {r['historical_sales']:>5}")

    print("\n" + "=" * 70)
    print("6. ROW LEVEL SECURITY (RLS) RESTRICTION COMPARISON")
    print("=" * 70)
    spokane_row = await conn.fetchrow("SELECT store_id, store_name FROM retail.stores WHERE store_name ILIKE '%Spokane%';")
    total_orders = await conn.fetchval("SELECT count(*) FROM retail.orders;")
    spokane_orders = await conn.fetchval("SELECT count(*) FROM retail.orders WHERE store_id = $1;", spokane_row['store_id'])
    print(f"Super Admin view: {total_orders:,} total orders across 8 stores")
    print(f"{spokane_row['store_name']} Store Manager view: {spokane_orders:,} orders (Store ID: {spokane_row['store_id']})")
    print(f"Isolation ratio: Spokane sees only {(spokane_orders / total_orders * 100):.2f}% of system data")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(deep_dive())
