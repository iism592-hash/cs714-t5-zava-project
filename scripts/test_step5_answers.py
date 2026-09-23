"""
test_step5_answers.py
Runs the exact answers to the 7 exploration questions in Step 5 of the guide.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://store_manager:StoreManager123!@127.0.0.1:15432/zava")
SUPER_ADMIN_ID = "00000000-0000-0000-0000-000000000000"

async def main():
    conn = await asyncpg.connect(POSTGRES_URL)
    await conn.execute(f"SET app.current_rls_user_id = '{SUPER_ADMIN_ID}';")

    print("\n" + "="*70)
    print("Q1: CATEGORY SEASONAL SWING & LEAD TIME")
    print("="*70)
    q1_rows = await conn.fetch("""
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
            MIN(qty) as min_monthly_qty,
            MAX(qty) as max_monthly_qty,
            ROUND((MAX(qty)::numeric / NULLIF(MIN(qty), 0)), 2) as swing_ratio
        FROM monthly
        GROUP BY category_name
        ORDER BY swing_ratio DESC;
    """)
    for r in q1_rows:
        print(f"{r['category_name']:<30} | Min: {r['min_monthly_qty']:>5} | Max: {r['max_monthly_qty']:>5} | Swing: {r['swing_ratio']}x")

    print("\n" + "="*70)
    print("Q2: STORES MOST AND LEAST ALIGNED TO NATIONAL SEASONALITY")
    print("="*70)
    q2_rows = await conn.fetch("""
        WITH national AS (
            SELECT 
                EXTRACT(MONTH FROM order_date)::int as mo,
                COUNT(*)::float / (SELECT COUNT(*) FROM retail.orders) as nat_share
            FROM retail.orders
            GROUP BY mo
        ),
        store_monthly AS (
            SELECT 
                s.store_name,
                EXTRACT(MONTH FROM o.order_date)::int as mo,
                COUNT(*)::float / SUM(COUNT(*)) OVER (PARTITION BY s.store_id) as store_share
            FROM retail.stores s
            JOIN retail.orders o ON s.store_id = o.store_id
            GROUP BY s.store_name, s.store_id, mo
        )
        SELECT 
            sm.store_name,
            ROUND(SUM(ABS(sm.store_share - n.nat_share))::numeric * 100, 2) as deviation_score
        FROM store_monthly sm
        JOIN national n ON sm.mo = n.mo
        GROUP BY sm.store_name
        ORDER BY deviation_score ASC;
    """)
    for r in q2_rows:
        print(f"{r['store_name']:<28} | Deviation: {r['deviation_score']}%")

    print("\n" + "="*70)
    print("Q3: WHAT HAPPENED IN 2023? (By Category & Store)")
    print("="*70)
    q3_cat = await conn.fetch("""
        SELECT 
            c.category_name,
            ROUND(SUM(CASE WHEN EXTRACT(YEAR FROM o.order_date) = 2022 THEN oi.unit_price * oi.quantity ELSE 0 END)::numeric, 2) as rev_2022,
            ROUND(SUM(CASE WHEN EXTRACT(YEAR FROM o.order_date) = 2023 THEN oi.unit_price * oi.quantity ELSE 0 END)::numeric, 2) as rev_2023,
            ROUND(((SUM(CASE WHEN EXTRACT(YEAR FROM o.order_date) = 2023 THEN oi.unit_price * oi.quantity ELSE 0 END) -
                    SUM(CASE WHEN EXTRACT(YEAR FROM o.order_date) = 2022 THEN oi.unit_price * oi.quantity ELSE 0 END)) /
                    NULLIF(SUM(CASE WHEN EXTRACT(YEAR FROM o.order_date) = 2022 THEN oi.unit_price * oi.quantity ELSE 0 END), 0) * 100)::numeric, 2) as pct_change
        FROM retail.categories c
        JOIN retail.products p ON c.category_id = p.category_id
        JOIN retail.order_items oi ON p.product_id = oi.product_id
        JOIN retail.orders o ON oi.order_id = o.order_id
        WHERE EXTRACT(YEAR FROM o.order_date) IN (2022, 2023)
        GROUP BY c.category_name
        ORDER BY pct_change ASC;
    """)
    for r in q3_cat:
        print(f"{r['category_name']:<30} | 2022: ${r['rev_2022']:>9,} | 2023: ${r['rev_2023']:>9,} ({r['pct_change']:>+6.2f}%)")

    print("\n" + "="*70)
    print("Q4: FREQUENTLY BOUGHT TOGETHER (Market Basket by Season)")
    print("="*70)
    q4_pairs = await conn.fetch("""
        SELECT 
            CASE 
                WHEN EXTRACT(MONTH FROM o.order_date) IN (6,7,8) THEN 'Summer'
                WHEN EXTRACT(MONTH FROM o.order_date) IN (12,1,2) THEN 'Winter'
                ELSE 'Spring/Fall'
            END as season,
            p1.product_name as prod1,
            p2.product_name as prod2,
            COUNT(*) as co_purchases
        FROM retail.order_items oi1
        JOIN retail.order_items oi2 ON oi1.order_id = oi2.order_id AND oi1.product_id < oi2.product_id
        JOIN retail.orders o ON oi1.order_id = o.order_id
        JOIN retail.products p1 ON oi1.product_id = p1.product_id
        JOIN retail.products p2 ON oi2.product_id = p2.product_id
        GROUP BY season, prod1, prod2
        ORDER BY co_purchases DESC
        LIMIT 6;
    """)
    for r in q4_pairs:
        print(f"[{r['season']:<11}] {r['prod1']} + {r['prod2']} ({r['co_purchases']} times)")

    print("\n" + "="*70)
    print("Q5 & Q6: INVENTORY MISALIGNMENT & VELOCITY GAP (Overstock / Transfer Candidates)")
    print("="*70)
    q5_rows = await conn.fetch("""
        WITH monthly_velocity AS (
            SELECT 
                oi.product_id,
                o.store_id,
                ROUND(SUM(oi.quantity)::numeric / 84, 2) as monthly_run_rate -- 84 months (7 yrs)
            FROM retail.order_items oi
            JOIN retail.orders o ON oi.order_id = o.order_id
            GROUP BY oi.product_id, o.store_id
        )
        SELECT 
            s.store_name,
            p.product_name,
            i.stock_level,
            COALESCE(mv.monthly_run_rate, 0.05) as monthly_velocity,
            ROUND((i.stock_level / NULLIF(mv.monthly_run_rate, 0))::numeric, 1) as months_of_supply
        FROM retail.inventory i
        JOIN retail.stores s ON i.store_id = s.store_id
        JOIN retail.products p ON i.product_id = p.product_id
        LEFT JOIN monthly_velocity mv ON i.product_id = mv.product_id AND i.store_id = mv.store_id
        WHERE mv.monthly_run_rate IS NOT NULL AND mv.monthly_run_rate > 0
        ORDER BY months_of_supply DESC
        LIMIT 5;
    """)
    for r in q5_rows:
        print(f"{r['store_name']:<24} | {r['product_name']:<30} | Stock: {r['stock_level']:>3} | Vel: {r['monthly_velocity']:>4}/mo | Supply: {r['months_of_supply']} mos")

    print("\n" + "="*70)
    print("Q7: SUPER ADMIN VS STORE MANAGER RLS SCOPE")
    print("="*70)
    stores = await conn.fetch("SELECT store_id, store_name FROM retail.stores ORDER BY store_id;")
    total_orders = await conn.fetchval("SELECT count(*) FROM retail.orders;")
    print(f"Super Admin Scope: {total_orders:,} orders across ALL stores\n")
    for s in stores:
        cnt = await conn.fetchval("SELECT count(*) FROM retail.orders WHERE store_id = $1;", s['store_id'])
        print(f"Store Manager {s['store_id']} ({s['store_name']:<22}): {cnt:>6,} orders ({cnt/total_orders*100:>5.2f}% of system data)")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
