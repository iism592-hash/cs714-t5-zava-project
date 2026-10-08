"""Transactional local integration tests: all workflow data is rolled back."""
import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from fastapi import FastAPI
from promotions import service
from promotions.db import connect
from promotions.auth import password_hash, verify_manager
from promotions.worker import due_day
from pathlib import Path
import sys

sys.path.insert(0, str(Path('src/python/web_app').resolve()))
from clearance import install_clearance_routes, apply_current_offers


async def main():
    assert service.recommend(5,50,100,60)[0]=='low_stock'
    assert service.recommend(300,30,100,60)[1]==20
    assert service.recommend(120,0,100,60)[1]==10
    assert service.recommend(50,5,100,60)[0]=='overstock'
    assert service.recommend(50,30,100,60) is None
    assert service.max_discount(100,95)==0
    assert due_day(datetime(2026,7,1,14,59,tzinfo=timezone.utc),'America/Los_Angeles',8) is None
    assert due_day(datetime(2026,7,1,15,0,tzinfo=timezone.utc),'America/Los_Angeles',8) is not None
    assert due_day(datetime(2026,12,1,16,0,tzinfo=timezone.utc),'America/Los_Angeles',8) is not None
    os.environ['PROMOTION_MANAGER_USERNAME']='fixture-manager'
    os.environ['PROMOTION_MANAGER_PASSWORD_HASH']=password_hash('fixture-secret')
    assert verify_manager('fixture-manager','fixture-secret')
    assert not verify_manager('visitor','fixture-secret')
    assert not verify_manager('fixture-manager','wrong')
    conn = await connect()
    transaction = conn.transaction()
    await transaction.start()
    class SharedConnection:
        def __getattr__(self, name): return getattr(conn, name)
        async def close(self): pass
    shared = SharedConnection()
    async def fixture_connect(): return shared
    service.connect = fixture_connect
    try:
        for filename in ('clearance_promotions.sql','inventory_promotions.sql'):
            await conn.execute((Path('data/database')/filename).read_text())
        p = await conn.fetchrow('SELECT product_id FROM retail.products ORDER BY product_id LIMIT 1')
        product_id = p['product_id']
        await conn.execute('UPDATE retail.products SET base_price=100,cost=60 WHERE product_id=$1',product_id)
        await conn.execute('UPDATE retail.inventory SET stock_level=1000 WHERE product_id=$1',product_id)
        await conn.execute('DELETE FROM retail.order_items WHERE product_id=$1',product_id)
        day = datetime.now(ZoneInfo('America/Los_Angeles')).date()
        first = await service.scan_inventory(day,'America/Los_Angeles')
        assert first['warning_count'] > 0
        assert (await service.scan_inventory(day,'America/Los_Angeles'))['skipped']=='already checked today'
        rec = await conn.fetchrow('SELECT * FROM retail.promotion_recommendations WHERE scan_day=$1 AND product_id=$2',day,product_id)
        rid=rec['recommendation_id']
        assert rec['status']=='pending'
        assert await conn.fetchval('SELECT COUNT(*) FROM retail.clearance_promotions WHERE recommendation_id=$1',rid)==0
        try:
            await service.decide(rid,'approved','fixture-manager',50,7,'invalid discount')
            raise AssertionError('50% discount accepted')
        except ValueError: pass
        await service.decide(rid,'approved','fixture-manager',10,7,'integration approval')
        assert await conn.fetchval('SELECT sale_price FROM retail.clearance_promotions WHERE recommendation_id=$1',rid)==Decimal('90.00')
        try:
            await service.decide(rid,'approved','fixture-manager',10,7,'duplicate')
            raise AssertionError('Duplicate approval accepted')
        except ValueError: pass
        await service.scan_inventory(day,'America/Los_Angeles',force=True)
        assert await conn.fetchval('SELECT status FROM retail.promotion_recommendations WHERE recommendation_id=$1',rid)=='approved'
        class Web:
            app=FastAPI()
            rls_user_id='00000000-0000-0000-0000-000000000000'
            async def _get_db_connection(self): return shared
        web=Web()
        install_clearance_routes(web)
        endpoint=next(r.endpoint for r in web.app.routes if r.path=='/api/clearance')
        visible=await endpoint(category=None,search=None,limit=100,offset=0)
        assert any(p['product_id']==product_id and p['sale_price']==90 for p in visible['products'])
        normal = await apply_current_offers(shared,[{'product_id':product_id,'base_price':100}])
        assert normal[0]['sale_price']==90
        await conn.execute("UPDATE retail.clearance_promotions SET starts_at=CURRENT_TIMESTAMP-INTERVAL '2 days', ends_at=CURRENT_TIMESTAMP-INTERVAL '1 day' WHERE recommendation_id=$1",rid)
        assert not any(p['product_id']==product_id for p in (await endpoint(category=None,search=None,limit=100,offset=0))['products'])
        assert 'sale_price' not in (await apply_current_offers(shared,[{'product_id':product_id,'base_price':100}]))[0]
        await conn.execute("UPDATE retail.clearance_promotions SET ends_at=CURRENT_TIMESTAMP+INTERVAL '1 day' WHERE recommendation_id=$1",rid)
        await service.decide(rid,'revoked','fixture-manager',reason='integration revocation')
        visible=await endpoint(category=None,search=None,limit=100,offset=0)
        assert not any(p['product_id']==product_id for p in visible['products'])
        assert await conn.fetchval('SELECT COUNT(*) FROM retail.promotion_decisions WHERE recommendation_id=$1',rid)==2
        # A rejected recommendation must not create a public offer.
        second = await conn.fetchrow("SELECT recommendation_id FROM retail.promotion_recommendations WHERE status='pending' LIMIT 1")
        if second:
            await service.decide(second['recommendation_id'],'rejected','fixture-manager',reason='do not promote')
            assert not await conn.fetchval('SELECT EXISTS(SELECT 1 FROM retail.clearance_promotions WHERE recommendation_id=$1)',second['recommendation_id'])
        print('PASS: stock rules, DST schedule, manager authentication, daily idempotency, capped approval, duplicate prevention, rescan preservation, B2C sale price, rejection, revocation and audit trail')
    finally:
        await transaction.rollback()
        await conn.close()


asyncio.run(main())
