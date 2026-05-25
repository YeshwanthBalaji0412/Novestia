"""Entry point for: python -m novestia.workers.price_worker"""

import asyncio

from novestia.workers.price_worker import main

asyncio.run(main())
