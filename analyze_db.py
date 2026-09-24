import asyncio
import os
import asyncpg

os.environ["POSTGRES_URL"] = "postgresql://store_manager:StoreManager123!@127.0.0.1:15432/zava"

async def main():
    conn = await asyncpg.connect(os.environ["POSTGRES_URL"])
    
    tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='retail'")
    for t in tables:
        t_name = t['table_name']
        cols = await conn.fetch(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='retail' AND table_name='{t_name}'")
        col_strs = [f"{c['column_name']} ({c['data_type']})" for c in cols]
        print(f"Table: {t_name}")
        print(f"Columns: {', '.join(col_strs)}\n")

    await conn.close()

asyncio.run(main())
