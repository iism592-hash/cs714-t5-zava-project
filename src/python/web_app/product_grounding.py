"""Keep streamed shopping links tied to verified, purchasable catalog records."""
import asyncio
import html
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import quote_plus


PRODUCT_LINK = re.compile(
    r'\[([^\]\n]+)\]\(\s*#product=[^\)\n]*\)'
    r'(?:[ \t]*(?:[-–—:][ \t]*)?\$[\d,]+(?:\.\d+)?)?', re.IGNORECASE
)


def normalized_name(name):
    return ' '.join(html.unescape(name).strip().casefold().split())


async def load_catalog(get_products):
    """Read every page; a partial/failed snapshot must not prove an item absent."""
    async def read_pages():
        products = []
        for offset in range(0, 10000, 200):
            page = await get_products(limit=200, offset=offset)
            if page.get('error') or not isinstance(page.get('products'), list):
                raise ValueError('Catalog unavailable')
            rows = page['products']
            products.extend(rows)
            if len(rows) < 200:
                return products
        raise ValueError('Catalog snapshot incomplete')
    return await asyncio.wait_for(read_pages(), timeout=15)


class ProductLinkGuard:
    """Buffer complete lines so split SSE tokens cannot expose an unchecked link."""
    def __init__(self, products):
        self.verified = products is not None
        self.products = {}
        self.pending = ''
        for product in products or []:
            key = normalized_name(product['product_name'])
            previous = self.products.get(key)
            if key in self.products and (previous is None or previous['sku'] != product['sku']):
                self.products[key] = None  # Ambiguous names are not cart identities.
            else:
                self.products[key] = product

    def clean(self, text):
        def replace(match):
            name = match.group(1)
            product = self.products.get(normalized_name(name))
            if not self.verified:
                return f'{name} (catalog unverified; prepare separately)'
            if not product:
                return f'{name} (not a verified Zava item; source separately)'
            try:
                amount = product.get('sale_price')
                price = Decimal(str(product['base_price'] if amount is None else amount))
                if not price.is_finite() or price < 0:
                    raise ValueError('Invalid price')
                if int(product.get('total_stock', 0)) <= 0:
                    return f'{name} (out of stock; source separately)'
            except (ValueError, TypeError, InvalidOperation):
                return f'{name} (catalog availability unverified; prepare separately)'
            exact_name = product['product_name']
            return (f'[{exact_name}](#product={quote_plus(exact_name)}) — '
                    f'${price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):.2f}')
        return PRODUCT_LINK.sub(replace, text)

    def feed(self, delta):
        self.pending += delta
        boundary = self.pending.rfind('\n')
        if boundary < 0:
            return ''
        ready, self.pending = self.pending[:boundary + 1], self.pending[boundary + 1:]
        return self.clean(ready)

    def finish(self):
        ready, self.pending = self.pending, ''
        return self.clean(ready)
