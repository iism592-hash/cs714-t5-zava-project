import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        host="zava-db-demo-2225.postgres.database.azure.com",
        user="zavaadmin",
        password="P@ssw0rdZava2026!",
        database="zava",
        ssl="require"
    )
    print(">> Connected as zavaadmin!")
    try:
        await conn.execute("CREATE USER store_manager WITH PASSWORD 'StoreManager123!';")
        print(">> Created user store_manager")
    except Exception as e:
        print(f">> Notice: {e}")
    await conn.execute("GRANT CONNECT ON DATABASE zava TO store_manager;")
    await conn.execute("GRANT USAGE ON SCHEMA retail TO store_manager;")
    await conn.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA retail TO store_manager;")
    await conn.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA retail TO store_manager;")
    print(">> Successfully granted store_manager permissions on schema retail!")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
