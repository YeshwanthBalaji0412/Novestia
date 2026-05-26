from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class HoldingSummary(BaseModel):
    ticker: str
    company_name: str
    quantity: str
    average_cost: str
    current_price: str
    market_value: str
    total_cost: str
    unrealized_pnl: str
    unrealized_pnl_pct: str
    daily_change: str
    daily_change_pct: str
    weight: str
    instrument_type: str
    sector: str | None


class PortfolioSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    cash_balance: str
    total_value: str
    starting_balance: str
    total_return: str
    total_return_pct: str
    daily_change: str
    daily_change_pct: str
    holdings: list[HoldingSummary]
    holdings_count: int


class HoldingDetailResponse(BaseModel):
    ticker: str
    company_name: str
    quantity: str
    average_cost: str
    current_price: str
    market_value: str
    total_cost: str
    unrealized_pnl: str
    unrealized_pnl_pct: str
    first_purchased_at: datetime | None
    recent_transactions: list[TransactionResponse]


class TransactionResponse(BaseModel):
    id: uuid.UUID
    ticker: str
    company_name: str | None = None
    type: str
    quantity: str
    execution_price: str
    total_amount: str
    realized_pnl: str | None
    executed_after_hours: bool
    journal_note: str | None
    executed_at: datetime


class PaginatedTransactionsResponse(BaseModel):
    data: list[TransactionResponse]
    next_cursor: str | None


class PerformancePoint(BaseModel):
    date: str
    value: str


class PerformanceResponse(BaseModel):
    starting_balance: str
    current_value: str
    total_return: str
    total_return_pct: str
    points: list[PerformancePoint]
