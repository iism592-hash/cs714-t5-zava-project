"""
analyze_zava_data.py
Exploratory Data Analysis script for the Zava DIY Retail Database.
Demonstrates Row-Level Security (RLS) Super Admin session context.
"""
import os
import asyncio
import asyncpg
from dotenv import load_dotenv

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://store_manager:StoreManager123!@127.0.0.1:15432/zava")
SUPER_ADMIN_ID = "00000000-0000-0000-0000-000000000000"

async def run_analysis():
    conn = await asyncpg.connect(POSTGRES_URL)
    
    # Set RLS Context to Super Admin to see all stores
    # In PostgreSQL RLS for Zava, app.current_rls_user_id controls tenant isolation
    try:
        await conn.execute(f"SET app.current_rls_user_id = '{SUPER_ADMIN_ID}';")
    except Exception:
        pass

    print("=" * 68)
    print(" ZAVA DIY RETAIL DATABASE - BUSINESS INTELLIGENCE REPORT")
    print(f" Context: Super Admin Access ({SUPER_ADMIN_ID})")
    print("=" * 68)

    # 1. Total Overview
    products = await conn.fetchval("SELECT count(*) FROM retail.products;")
    stores = await conn.fetchval("SELECT count(*) FROM retail.stores;")
    customers = await conn.fetchval("SELECT count(*) FROM retail.customers;")
    orders = await conn.fetchval("SELECT count(*) FROM retail.orders;")
    order_items = await conn.fetchval("SELECT count(*) FROM retail.order_items;")
    print(f"\n[1] High-Level Metrics:")
    print(f"   - Total Products in Catalog:  {products:>10,}")
    print(f"   - Total Stores:               {stores:>10}")
    print(f"   - Total Registered Customers: {customers:>10,}")
    print(f"   - Total Historical Orders:    {orders:>10,}")
    print(f"   - Total Order Line Items:     {order_items:>10,}")

    # 2. Store Performance Ranking (Revenue & Order Volume)
    store_query = """
        SELECT 
            s.store_name,
            COUNT(DISTINCT o.order_id) as total_orders,
            ROUND(SUM(oi.unit_price * oi.quantity)::numeric, 2) as total_revenue
        FROM retail.stores s
        JOIN retail.orders o ON s.store_id = o.store_id
        JOIN retail.order_items oi ON o.order_id = oi.order_id
        GROUP BY s.store_name
        ORDER BY total_revenue DESC;
    """
    store_rows = await conn.fetch(store_query)
    print(f"\n[2] Store Performance (Ranked by Total Revenue):")
    print(f"   {'Store Location':<24} | {'Total Orders':>14} | {'Total Revenue':>18}")
    print("   " + "-" * 62)
    for r in store_rows:
        print(f"   {r['store_name']:<24} | {r['total_orders']:>14,} | ${r['total_revenue']:>17,}")

    # 3. Top 5 Best-Selling Products (by Revenue)
    top_products_query = """
        SELECT 
            p.product_name,
            c.category_name,
            SUM(oi.quantity) as units_sold,
            ROUND(SUM(oi.unit_price * oi.quantity)::numeric, 2) as total_sales
        FROM retail.products p
        JOIN retail.categories c ON p.category_id = c.category_id
        JOIN retail.order_items oi ON p.product_id = oi.product_id
        GROUP BY p.product_name, c.category_name
        ORDER BY total_sales DESC
        LIMIT 5;
    """
    top_rows = await conn.fetch(top_products_query)
    print(f"\n[3] Top 5 Best-Selling Products (by Revenue):")
    for i, r in enumerate(top_rows, 1):
        print(f"   {i}. {r['product_name']} ({r['category_name']})")
        print(f"      Units Sold: {r['units_sold']:,} | Revenue Generated: ${r['total_sales']:,}")

    # 4. Category Breakdown
    cat_query = """
        SELECT 
            c.category_name,
            COUNT(DISTINCT p.product_id) as product_count,
            ROUND(SUM(oi.unit_price * oi.quantity)::numeric, 2) as category_revenue
        FROM retail.categories c
        JOIN retail.products p ON c.category_id = p.category_id
        JOIN retail.order_items oi ON p.product_id = oi.product_id
        GROUP BY c.category_name
        ORDER BY category_revenue DESC;
    """
    cat_rows = await conn.fetch(cat_query)
    print(f"\n[4] Revenue Breakdown by Product Category:")
    print(f"   {'Category Name':<30} | {'Products':>8} | {'Category Revenue':>18}")
    print("   " + "-" * 62)
    for r in cat_rows:
        print(f"   {r['category_name']:<30} | {r['product_count']:>8} | ${r['category_revenue']:>17,}")

    print("\n" + "=" * 68)
    await conn.close()

if __name__ == "__main__":
    asyncio.run(run_analysis())
