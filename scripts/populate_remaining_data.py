import asyncio
import logging
import os
import sys
from pathlib import Path

# Add data/database to path
db_dir = Path(__file__).resolve().parent.parent / "data" / "database"
sys.path.insert(0, str(db_dir))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

import generate_zava_postgres as gen

async def populate():
    print("Connecting to Azure PostgreSQL as zavaadmin...")
    conn = await gen.asyncpg.connect(
        host="zava-db-demo-2225.postgres.database.azure.com",
        port=5432,
        user="zavaadmin",
        password="P@ssw0rdZava2026!",
        database="zava",
        ssl="require"
    )
    print("Connected successfully!")
    
    try:
        # Check if customers already exist
        c_count = await conn.fetchval(f"SELECT count(*) FROM {gen.SCHEMA_NAME}.customers")
        if c_count == 0:
            print("Populating 250 customers...")
            await gen.insert_customers(conn, num_customers=250)
        else:
            print(f"Customers already exist ({c_count})")
            
        # Check inventory
        i_count = await conn.fetchval(f"SELECT count(*) FROM {gen.SCHEMA_NAME}.inventory")
        if i_count == 0:
            print("Populating inventory across all stores...")
            await gen.insert_inventory(conn)
        else:
            print(f"Inventory already exists ({i_count})")
            
        # Check orders
        o_count = await conn.fetchval(f"SELECT count(*) FROM {gen.SCHEMA_NAME}.orders")
        if o_count == 0:
            print("Populating orders & order_items for customers...")
            await gen.insert_orders(conn, num_customers=250)
        else:
            print(f"Orders already exist ({o_count})")
            
        print("\nAll remaining tables populated successfully!")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(populate())
