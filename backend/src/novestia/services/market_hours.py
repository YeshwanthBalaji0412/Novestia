"""Market hours detection for US equities."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


def is_market_open(dt: datetime | None = None) -> bool:
    """Check if US stock market is currently open."""
    dt = datetime.now(ET) if dt is None else dt.astimezone(ET)

    # Weekend
    if dt.weekday() >= 5:
        return False

    current_time = dt.time()
    return MARKET_OPEN <= current_time < MARKET_CLOSE
