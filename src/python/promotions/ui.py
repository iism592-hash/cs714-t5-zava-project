import asyncio
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from .auth import verify_manager
from .service import dashboard, scan_inventory, decide, max_discount


def render_inventory_dashboard():
    st.subheader('Inventory warnings & promotion review')
    timezone = os.getenv('INVENTORY_CHECK_TIMEZONE', 'America/Los_Angeles')
    hour = int(os.getenv('INVENTORY_CHECK_HOUR', '8'))
    st.caption(f'Daily inventory check: {hour:02}:00 {timezone}. Discounts require manager approval.')
    actor = st.session_state.get('promotion_manager')
    if actor and time.time() - st.session_state.get('promotion_login_at', 0) > 3600:
        st.session_state.pop('promotion_manager', None)
        actor = None
    if not actor:
        if not os.getenv('PROMOTION_MANAGER_PASSWORD_HASH'):
            st.warning('Promotion review is unavailable until a manager login is configured.')
            return
        with st.form('promotion_login', clear_on_submit=True):
            username = st.text_input('Manager username')
            password = st.text_input('Manager password', type='password')
            submitted = st.form_submit_button('Sign in to review inventory')
        if submitted:
            blocked_until = st.session_state.get('promotion_login_blocked_until', 0)
            if time.time() < blocked_until:
                st.error('Too many attempts. Please wait one minute.')
            elif verify_manager(username, password):
                st.session_state['promotion_manager'] = os.environ['PROMOTION_MANAGER_USERNAME']
                st.session_state['promotion_login_at'] = time.time()
                st.session_state['promotion_login_attempts'] = 0
                st.rerun()
            else:
                attempts = st.session_state.get('promotion_login_attempts', 0) + 1
                st.session_state['promotion_login_attempts'] = attempts
                if attempts >= 5:
                    st.session_state['promotion_login_blocked_until'] = time.time() + 60
                    st.session_state['promotion_login_attempts'] = 0
                st.error('Invalid manager credentials.')
        return
    st.caption(f'Signed in as {actor}; session expires after one hour.')
    if st.button('Sign out of promotion review'):
        st.session_state.pop('promotion_manager', None)
        st.rerun()
    if st.button('Check inventory now'):
        try:
            with st.spinner('Checking current stock and last 30 days of sales...'):
                asyncio.run(scan_inventory(datetime.now(ZoneInfo(timezone)).date(), timezone, force=True))
            st.success('Inventory check completed. Existing manager decisions are preserved.')
        except Exception:
            st.error('Inventory check failed. No approvals were changed; consult the service log.')
    try:
        run, rows = asyncio.run(dashboard())
    except Exception:
        st.error('Inventory dashboard could not load. Check database migrations and permissions.')
        return
    if not run:
        st.info('No inventory check yet. Use Check inventory now or wait for the morning check.')
        return
    st.caption(f"Last check: {run['completed_at']} · {run['warning_count']} warnings · Latest recorded sale: {run['latest_order_date']}")
    if run['latest_order_date'] is None or (datetime.now(ZoneInfo(timezone)).date() - run['latest_order_date']).days > 30:
        st.warning('Sales data is older than 30 days or missing. Verify freshness before approving a discount.')
    st.info('Recommendations use stock and sales rules: overstock at ≥90 days of cover (or ≥100 units with no recent sales); low stock at ≤10 units or <7 days of cover. Discount cap 20%; minimum gross margin 10%.')
    if not rows:
        st.success('No inventory warnings.')
        return
    st.dataframe([{k: r[k] for k in ('recommendation_id','product_name','warning_type','stock_level','sold_30_days','suggested_discount','status')} for r in rows], hide_index=True, use_container_width=True)
    row = st.selectbox('Select a recommendation', rows,
        format_func=lambda r: f"#{r['recommendation_id']} · {r['product_name']} · {r['status']}")
    st.write(row['reason'])
    st.caption(f"SKU {row['sku']} · Base price ${row['base_price']:.2f} · Cost ${row['cost']:.2f}")
    if st.button('Ask AI to explain this recommendation'):
        from services.zava_agent_core import get_agent_response
        prompt = f"Explain this inventory recommendation using ONLY these supplied facts. Do not invent competitor prices, demand or weather. Do not approve or write any discount. Product {row['product_name']}, stock {row['stock_level']}, units sold last 30 days {row['sold_30_days']}, suggested discount {row['suggested_discount']}%, reason: {row['reason']}. Explain uncertainties and recommend whether the manager should consider promotion, under 150 words."
        try:
            with st.spinner('Preparing AI explanation...'):
                st.write(asyncio.run(get_agent_response(prompt, '')))
        except Exception:
            st.error('AI explanation is unavailable. The inventory facts and review controls remain available.')
    if row['status'] == 'pending':
        maximum = max_discount(row['base_price'], row['cost']) if row['warning_type']=='overstock' else 0
        with st.form(f"promotion_decision_{row['recommendation_id']}"):
            discount = st.number_input('Discount (%)', min_value=0, max_value=maximum, value=min(row['suggested_discount'],maximum), step=1)
            days = st.number_input('Offer duration (days)', min_value=1, max_value=30, value=7, step=1)
            reason = st.text_input('Decision reason (required)')
            approve = st.form_submit_button('Approve promotion', disabled=maximum==0)
            reject = st.form_submit_button('Reject recommendation')
        if approve or reject:
            try:
                asyncio.run(decide(row['recommendation_id'], 'approved' if approve else 'rejected', actor, discount, days, reason))
                st.session_state['promotion_notice'] = 'Decision saved. Approved offers are visible in B2C.' if approve else 'Recommendation rejected; no offer created.'
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error('Decision could not be saved. Refresh before retrying.')
    elif row['status']=='approved':
        st.write(f"Approved offer: ${row['sale_price']:.2f} · Ends {row['ends_at']}")
        with st.form(f"promotion_revoke_{row['recommendation_id']}"):
            reason = st.text_input('Revocation reason (required)')
            revoke = st.form_submit_button('Revoke offer')
        if revoke:
            try:
                asyncio.run(decide(row['recommendation_id'],'revoked',actor,reason=reason))
                st.session_state['promotion_notice'] = 'Offer revoked. It is no longer returned to B2C.'
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error('Revocation could not be saved.')
    if notice := st.session_state.pop('promotion_notice', None):
        st.success(notice)
