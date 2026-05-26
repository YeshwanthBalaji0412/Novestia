from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class WatchlistItemResponse(BaseModel):
    ticker: str
    company_name: str
    current_price: str
    previous_close: str
    daily_change: str
    daily_change_pct: str
    added_at: datetime


class WatchlistAddResponse(BaseModel):
    ticker: str
    added_at: datetime
