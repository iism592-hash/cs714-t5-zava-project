import asyncio
import asyncpg

async def fix_user():
    print("Connecting as zavaadmin...")
    conn = await asyncpg.connect(
        host="zava-db-demo-2225.postgres.database.azure.com",
        port=5432,
        user="zavaadmin",
        password="P@ssw0rdZava2026!",
        database="zava",
        ssl="require"
    )
    print("Connected successfully!")
    
    # Check if store_manager exists
    row = await conn.fetchrow("SELECT rolname FROM pg_roles WHERE rolname = 'store_manager'")
    if not row:
        print("Creating role store_manager...")
        await conn.execute("CREATE ROLE store_manager WITH LOGIN PASSWORD 'StoreManager123!'")
    else:
        print("Altering password for store_manager...")
        await conn.execute("ALTER ROLE store_manager WITH LOGIN PASSWORD 'StoreManager123!'")
        
    print("Granting permissions...")
    await conn.execute("GRANT ALL PRIVILEGES ON DATABASE zava TO store_manager")
    await conn.execute("GRANT ALL PRIVILEGES ON SCHEMA public TO store_manager")
    await conn.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO store_manager")
    await conn.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO store_manager")
    await conn.execute("GRANT ALL PRIVILEGES ON ALL ROUTINES IN SCHEMA public TO store_manager")
    await conn.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO store_manager")
    print("All privileges granted to store_manager successfully!")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(fix_user())
