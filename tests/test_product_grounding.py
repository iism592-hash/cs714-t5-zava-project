"""Regression: safety advice must not manufacture purchasable catalog products."""
import json
import unittest
from unittest.mock import patch
from product_grounding import ProductLinkGuard, load_catalog


PRODUCT = {'product_name': 'GFCI Outlet 20-Amp', 'sku': 'GFCI',
           'base_price': 26.87, 'total_stock': 12}
BLUEPRINT = ('Tools: [GFCI Outlet 20-Amp](#product=Outlet) — $18.99\n'
             'Use [Insulated Gloves](#product=Gloves) — $12.00 and '
             '[Safety Glasses](#product=Safety+Glasses) for protection.\n'
             'Turn off power and verify it is off.')


class GroundingTests(unittest.IsolatedAsyncioTestCase):
    def test_split_tokens_and_safety_retained(self):
        guard = ProductLinkGuard([PRODUCT])
        result = ''.join(guard.feed(token) for token in BLUEPRINT) + guard.finish()
        self.assertIn('[GFCI Outlet 20-Amp](#product=GFCI+Outlet+20-Amp) — $26.87', result)
        self.assertEqual(result.count('](#product='), 1)
        self.assertIn('Insulated Gloves (not a verified Zava item; source separately)', result)
        self.assertIn('Safety Glasses (not a verified Zava item; source separately)', result)
        self.assertIn('Turn off power and verify it is off.', result)
        self.assertNotIn('$12.00', result)
        self.assertNotIn('$18.99', result)

    def test_price_stock_ambiguity_and_failed_catalog(self):
        link = '[GFCI Outlet 20-Amp](#product=Outlet)'
        self.assertIn('$0.00', ProductLinkGuard([{**PRODUCT, 'sale_price': 0}]).clean(link))
        self.assertIn('$26.87', ProductLinkGuard([{**PRODUCT, 'sale_price': None}]).clean(link))
        for products in ([{**PRODUCT, 'total_stock': 0}],
                         [{**PRODUCT, 'base_price': 'NaN'}],
                         [PRODUCT, {**PRODUCT, 'sku': 'OTHER'}], None):
            self.assertNotIn('](#product=', ProductLinkGuard(products).clean(link))
        self.assertIn('catalog unverified', ProductLinkGuard(None).clean(link))

    async def test_pagination_and_fail_closed(self):
        offsets = []
        async def pages(limit, offset):
            offsets.append(offset)
            return {'products': [PRODUCT] * (limit if offset == 0 else 1)}
        self.assertEqual(len(await load_catalog(pages)), 201)
        self.assertEqual(offsets, [0, 200])
        async def broken(limit, offset):
            return {'products': [], 'error': 'Database offline'}
        with self.assertRaises(ValueError):
            await load_catalog(broken)

    async def test_actual_web_stream_and_saved_session(self):
        from web_app import WebApp
        instance = WebApp.__new__(WebApp)
        instance.chat_sessions = {'fixture': []}
        async def catalog(limit, offset):
            return {'products': [PRODUCT]}
        instance.get_products = catalog
        class Response:
            status_code = 200
            async def aiter_text(self):
                for token in BLUEPRINT:
                    yield 'data: ' + json.dumps({'content': token}) + '\n\n'
                yield 'data: ' + json.dumps({'done': True}) + '\n\n'
        class Client:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return False
            def stream(self, *args, **kwargs):
                class Stream(Client):
                    async def __aenter__(self):
                        return Response()
                return Stream()
        with patch('web_app.httpx.AsyncClient', return_value=Client()):
            events = [event async for event in instance._generate_stream('fixture', 'fixture')]
        content = ''.join(json.loads(e[6:])['content'] for e in events
                          if e.startswith('data: {') and 'content' in json.loads(e[6:]))
        self.assertEqual(content.count('](#product='), 1)
        self.assertIn('$26.87', content)
        self.assertEqual(instance.chat_sessions['fixture'][0]['content'], content)
        self.assertEqual(events[-1], 'data: [DONE]\n\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
