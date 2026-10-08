"""Apply workflow schema and narrowly scoped app-role grants using an admin connection.

PGHOST, PGUSER and PGPASSWORD must be supplied securely (never logged).
Run from the repository root; PostgreSQL supports transactionally rolling back DDL.
"""
import asyncio
import os
from pathlib import Path
import asyncpg


async def main():
    conn = await asyncpg.connect(host=os.environ['PGHOST'],user=os.environ['PGUSER'],
        password=os.environ['PGPASSWORD'],database='zava',ssl='require',timeout=30)
    try:
        async with conn.transaction():
            for name in ('clearance_promotions.sql','inventory_promotions.sql'):
                await conn.execute((Path('data/database') / name).read_text())
            for role in ('zava-b2b-fntj','zava-b2c-fntj'):
                if not await conn.fetchval('SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=$1)',role):
                    raise ValueError(f'Expected app role {role} does not exist')
            await conn.execute('GRANT SELECT ON retail.clearance_promotions TO "zava-b2c-fntj"')
            await conn.execute('GRANT SELECT, INSERT, UPDATE ON retail.clearance_promotions, retail.inventory_scan_runs, retail.promotion_recommendations TO "zava-b2b-fntj"')
            await conn.execute('GRANT DELETE ON retail.promotion_recommendations TO "zava-b2b-fntj"')
            await conn.execute('GRANT SELECT, INSERT ON retail.promotion_decisions TO "zava-b2b-fntj"')
            for table in ('clearance_promotions','promotion_recommendations','promotion_decisions'):
                seq = await conn.fetchval('SELECT pg_get_serial_sequence($1,$2)',f'retail.{table}',
                    {'clearance_promotions':'promotion_id','promotion_recommendations':'recommendation_id','promotion_decisions':'decision_id'}[table])
                # Sequence identifier comes from PostgreSQL metadata for fixed tables.
                await conn.execute(f'GRANT USAGE ON SEQUENCE {seq} TO "zava-b2b-fntj"')
        print('Workflow schema applied; B2C read-only and B2B review grants configured. No offers approved.')
    finally:
        await conn.close()


if __name__=='__main__':
    asyncio.run(main())
