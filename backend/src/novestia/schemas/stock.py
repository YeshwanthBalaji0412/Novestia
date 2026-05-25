from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class StockSearchResult(BaseModel):
    ticker: str
    company_name: str
    exchange: str | None = None
    instrument_type: str

    model_config = {"from_attributes": True}


class StockQuote(BaseModel):
    ticker: str
    price: str  # NUMERIC as string
    previous_close: str
    change: str
    change_pct: str
    market_open: bool
    stale: bool = False
    updated_at: datetime


class StockSnapshotResponse(BaseModel):
    ticker: str
    company_name: str
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    instrument_type: str
    last_price: str | None = None
    previous_close: str | None = None
    market_cap: int | None = None
    pe_ratio: str | None = None
    eps: str | None = None
    dividend_yield: str | None = None
    week_52_high: str | None = None
    week_52_low: str | None = None
    beta: str | None = None
    expense_ratio: str | None = None
    snapshot_taken_at: datetime | None = None


class HistoryPoint(BaseModel):
    timestamp: datetime
    open: str
    high: str
    low: str
    close: str
    volume: int | None = None


class StockHistoryResponse(BaseModel):
    ticker: str
    range: str
    interval: str
    points: list[HistoryPoint]
