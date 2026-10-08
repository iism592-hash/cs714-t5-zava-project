"""Daily durable inventory check, with catch-up after restart and DST support."""
import asyncio
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from .service import scan_inventory


def due_day(now, timezone, hour):
    local = now.astimezone(ZoneInfo(timezone))
    return local.date() if local.hour >= hour else None


async def main():
    logging.basicConfig(level=logging.INFO)
    timezone = os.getenv('INVENTORY_CHECK_TIMEZONE', 'America/Los_Angeles')
    hour = int(os.getenv('INVENTORY_CHECK_HOUR', '8'))
    if not 0 <= hour <= 23:
        raise ValueError('INVENTORY_CHECK_HOUR must be 0–23')
    handled = None
    while True:
        day = due_day(datetime.now().astimezone(), timezone, hour)
        if day and day != handled:
            try:
                result = await scan_inventory(day, timezone)
                if result.get('skipped') != 'scan already running':
                    handled = day
                logging.info('Inventory check %s: %s', day, result)
            except Exception:
                logging.exception('Inventory check failed; retry in 60 seconds')
        await asyncio.sleep(60)


if __name__ == '__main__':
    asyncio.run(main())
