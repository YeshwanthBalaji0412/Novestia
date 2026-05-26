from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TradeRequest(BaseModel):
    ticker: str
    type: str = Field(pattern="^(BUY|SELL)$")
    quantity: str = Field(description="Decimal quantity as string")
    journal_note: str = Field(min_length=1, max_length=500)


class TradePreviewRequest(BaseModel):
    ticker: str
    type: str = Field(pattern="^(BUY|SELL)$")
    quantity: str


class TransactionResult(BaseModel):
    id: uuid.UUID
    ticker: str
    type: str
    quantity: str
    execution_price: str
    total_amount: str
    realized_pnl: str | None
    executed_after_hours: bool
    journal_note: str
    executed_at: datetime


class PortfolioAfter(BaseModel):
    cash_balance: str
    total_value: str | None = None


class HoldingAfter(BaseModel):
    ticker: str
    quantity: str
    average_cost: str


class TradeResponse(BaseModel):
    transaction: TransactionResult
    portfolio_after: PortfolioAfter
    holding_after: HoldingAfter | None
    risk_score_after: int | None = None


class TradeWarning(BaseModel):
    code: str
    message: str


class TradePreviewResponse(BaseModel):
    ticker: str
    type: str
    quantity: str
    estimated_price: str
    estimated_total: str
    market_open: bool
    after_hours: bool
    portfolio_after: PortfolioAfter
    holding_after: HoldingAfter | None
    warnings: list[TradeWarning]
