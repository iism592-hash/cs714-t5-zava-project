"""Verify Streamlit manager gating and zero-discount controls render correctly."""
import os
from promotions.auth import password_hash
from streamlit.testing.v1 import AppTest

os.environ['PROMOTION_MANAGER_USERNAME']='fixture-manager'
os.environ['PROMOTION_MANAGER_PASSWORD_HASH']=password_hash('fixture-secret')
code='''
import streamlit as st
from datetime import datetime, date, timezone
import promotions.ui as ui
async def fixture_dashboard():
    return ({'completed_at':datetime.now(timezone.utc),'warning_count':1,'latest_order_date':date.today()},
      [{'recommendation_id':1,'product_name':'Local Fixture','sku':'FIXTURE',
        'warning_type':'low_stock','stock_level':5,'sold_30_days':50,
        'suggested_discount':0,'status':'pending','reason':'Restock; no discount.',
        'base_price':100,'cost':60}])
ui.dashboard=fixture_dashboard
ui.render_inventory_dashboard()
'''
app=AppTest.from_string(code).run()
assert not app.exception
assert not any(b.label=='Approve promotion' for b in app.button)
app.text_input[0].set_value('fixture-manager')
app.text_input[1].set_value('wrong')
app.button[0].click().run()
assert app.error[0].value=='Invalid manager credentials.'
app.text_input[0].set_value('fixture-manager')
app.text_input[1].set_value('fixture-secret')
app.button[0].click().run()
assert not app.exception
assert app.session_state['promotion_manager']=='fixture-manager'
approve=next(b for b in app.button if b.label=='Approve promotion')
assert approve.disabled
assert any(b.label=='Reject recommendation' for b in app.button)
print('PASS: anonymous users cannot review; invalid login denied; valid login works; low-stock discount disabled')
