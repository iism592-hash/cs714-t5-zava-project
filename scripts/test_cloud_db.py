import asyncio
import sys
import json
from pathlib import Path

# Add customer_sales to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "python" / "mcp_server" / "customer_sales"))
from customer_sales_postgres import PostgreSQLCustomerSales

async def main():
    conn_str = "postgresql://store_manager:StoreManager123!@zava-db-demo-2225.postgres.database.azure.com:5432/zava?sslmode=require"
    db = PostgreSQLCustomerSales(conn_str)
    await db.create_pool()
    
    # Test with Super Manager UUID: 00000000-0000-0000-0000-000000000000
    super_manager_id = "00000000-0000-0000-0000-000000000000"
    result_json = await db.get_products_by_name("hammer", 5, super_manager_id)
    data = json.loads(result_json)
    results = data.get("results", [])
    print(f">> Cloud Postgres query SUCCESS! Found {len(results)} products:")
    for p in results:
        print(f"   * {p.get('product_name')} | Type: {p.get('type_name')} | Price: ${p.get('price')} | Total Stock: {p.get('total_stock')}")
        
    await db.close_pool()

if __name__ == "__main__":
    asyncio.run(main())
