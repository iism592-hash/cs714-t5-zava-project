import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host="zava-db-demo-2225.postgres.database.azure.com",
        port=5432,
        user="store_manager",
        password="StoreManager123!",
        database="zava",
        ssl="require"
    )
    tables = [
        "categories", "product_types", "products", "stores",
        "inventory", "customers", "orders", "order_items",
        "product_description_embeddings", "product_image_embeddings"
    ]
    for t in tables:
        count = await conn.fetchval(f"SELECT count(*) FROM retail.{t}")
        print(f"retail.{t}: {count} rows")
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
