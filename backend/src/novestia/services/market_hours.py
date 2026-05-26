"""Market hours detection for US equities.

Handles weekdays 9:30am-4:00pm ET, excluding US market holidays.
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

# US stock market holidays for 2025 and 2026.
# Add more years as needed or switch to pandas_market_calendars post-MVP.
_US_MARKET_HOLIDAYS: set[date] = {
    # 2025
    date(2025, 1, 1),    # New Year's Day
    date(2025, 1, 20),   # MLK Day
    date(2025, 2, 17),   # Presidents' Day
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 26),   # Memorial Day
    date(2025, 6, 19),   # Juneteenth
    date(2025, 7, 4),    # Independence Day
    date(2025, 9, 1),    # Labor Day
    date(2025, 11, 27),  # Thanksgiving
    date(2025, 12, 25),  # Christmas
    # 2026
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # MLK Day
    date(2026, 2, 16),   # Presidents' Day
    date(2026, 4, 3),    # Good Friday
    date(2026, 5, 25),   # Memorial Day
    date(2026, 6, 19),   # Juneteenth
    date(2026, 7, 3),    # Independence Day (observed)
    date(2026, 9, 7),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving
    date(2026, 12, 25),  # Christmas
}


def is_market_open(dt: datetime | None = None) -> bool:
    """Check if US stock market is currently open.

    Returns False for weekends, US market holidays, and outside 9:30-16:00 ET.
    """
    dt = datetime.now(ET) if dt is None else dt.astimezone(ET)

    # Weekend
    if dt.weekday() >= 5:
        return False

    # US market holiday
    if dt.date() in _US_MARKET_HOLIDAYS:
        return False

    current_time = dt.time()
    return MARKET_OPEN <= current_time < MARKET_CLOSE
