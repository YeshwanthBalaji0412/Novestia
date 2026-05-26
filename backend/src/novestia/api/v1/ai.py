"""AI explanation endpoints."""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.auth import get_current_user
from novestia.core.db import get_db
from novestia.core.errors import AppError
from novestia.core.redis import get_redis
from novestia.models.portfolio import Portfolio
from novestia.models.stock import Stock, StockSnapshot
from novestia.models.user import User
from novestia.services import ai_service, risk_service

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


async def _rate_limit(user_id: str, redis: aioredis.Redis) -> None:
    """20 AI calls per minute per user."""
    key = f"ai:rate:{user_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > 20:
        raise AppError(
            code="RATE_LIMITED",
            message="AI explanation rate limit reached (20/min).",
            status_code=429,
        )


class ExplainStockRequest(BaseModel):
    ticker: str


class ExplainMetricRequest(BaseModel):
    metric_name: str = Field(
        pattern=(
            "^(pe_ratio|eps|market_cap|beta|dividend_yield"
            "|expense_ratio|week_52_high|week_52_low)$"
        )
    )
    ticker: str | None = None


@router.post("/explain-stock")
async def explain_stock(
    request: ExplainStockRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    await _rate_limit(str(user.id), redis)

    ticker = request.ticker.upper()

    # Load stock + snapshot data
    result = await db.execute(
        select(Stock, StockSnapshot)
        .outerjoin(StockSnapshot, Stock.ticker == StockSnapshot.ticker)
        .where(Stock.ticker == ticker)
    )
    row = result.one_or_none()
    if not row:
        raise AppError(
            code="NOT_FOUND",
            message=f"Stock {ticker} not found",
            status_code=404,
        )
    stock, snapshot = row

    snapshot_data = {
        "company_name": stock.company_name,
        "exchange": stock.exchange,
        "sector": stock.sector,
        "industry": stock.industry,
        "instrument_type": stock.instrument_type,
        "last_price": str(snapshot.last_price) if snapshot else "N/A",
        "market_cap": str(snapshot.market_cap) if snapshot else "N/A",
        "pe_ratio": str(snapshot.pe_ratio) if snapshot and snapshot.pe_ratio else "N/A",
        "eps": str(snapshot.eps) if snapshot and snapshot.eps else "N/A",
        "beta": str(snapshot.beta) if snapshot and snapshot.beta else "N/A",
        "dividend_yield": (
            str(snapshot.dividend_yield) if snapshot and snapshot.dividend_yield else "N/A"
        ),
        "week_52_low": str(snapshot.week_52_low) if snapshot and snapshot.week_52_low else "N/A",
        "week_52_high": (
            str(snapshot.week_52_high) if snapshot and snapshot.week_52_high else "N/A"
        ),
    }

    explanation = await ai_service.explain_stock(ticker, snapshot_data, db)
    return {"data": {"ticker": ticker, **explanation}}


@router.post("/explain-risk")
async def explain_risk(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    await _rate_limit(str(user.id), redis)

    # Get user's portfolio
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise AppError(code="NOT_FOUND", message="Portfolio not found", status_code=404)

    # Get latest risk report
    report = await risk_service.get_latest(portfolio.id, db)
    if not report:
        raise AppError(
            code="NOT_FOUND",
            message="No risk report found. Make a trade first.",
            status_code=404,
        )

    interpretation = await ai_service.explain_risk(
        report.engine_explanation, str(report.id), db
    )
    return {"data": {"risk_report_id": str(report.id), **interpretation}}


@router.post("/explain-metric")
async def explain_metric(
    request: ExplainMetricRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    await _rate_limit(str(user.id), redis)

    metric_value = None
    if request.ticker:
        ticker = request.ticker.upper()
        result = await db.execute(
            select(StockSnapshot).where(StockSnapshot.ticker == ticker)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot:
            metric_value = str(getattr(snapshot, request.metric_name, None) or "")

    explanation = await ai_service.explain_metric(
        request.metric_name, request.ticker, metric_value, db
    )
    return {"data": {"metric": request.metric_name, **explanation}}
