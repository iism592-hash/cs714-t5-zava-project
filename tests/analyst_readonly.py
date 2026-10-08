import asyncio
import asyncpg
from promotions.db import connect
from promotions.readonly import fetch_analysis_rows


async def main():
    conn=await connect()
    try:
        assert (await fetch_analysis_rows(conn,'SELECT 1 AS value'))[0]['value']==1
        for query in (
            'UPDATE retail.products SET base_price=base_price WHERE FALSE RETURNING product_id',
            'WITH changed AS (UPDATE retail.products SET base_price=base_price WHERE FALSE RETURNING product_id) SELECT * FROM changed',
        ):
            try:
                await fetch_analysis_rows(conn,query)
                raise AssertionError('Analyst write query accepted')
            except asyncpg.ReadOnlySQLTransactionError:
                pass
        assert (await fetch_analysis_rows(conn,'SELECT 2 AS value'))[0]['value']==2
        print('PASS: analyst reads allowed; UPDATE and write CTE blocked; connection usable after rejection')
    finally:
        await conn.close()


asyncio.run(main())
