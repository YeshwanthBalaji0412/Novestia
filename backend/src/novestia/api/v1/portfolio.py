"""Portfolio read endpoints — dashboard, holdings, transactions, performance."""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.auth import get_current_user
from novestia.core.db import get_db
from novestia.core.errors import AppError
from novestia.core.redis import get_redis
from novestia.models.portfolio import Portfolio
from novestia.models.user import User
from novestia.services import portfolio_service

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


async def _get_user_portfolio(
    user: User, db: AsyncSession
) -> Portfolio:
    """Get the user's portfolio, raising 404 if not found."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise AppError(
            code="NOT_FOUND",
            message="Portfolio not found. Complete onboarding first.",
            status_code=404,
        )
    return portfolio


@router.get("")
async def get_portfolio(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    portfolio = await _get_user_portfolio(user, db)
    summary = await portfolio_service.get_portfolio_summary(portfolio, db, redis)
    return {"data": summary.model_dump()}


@router.get("/holdings/{ticker}")
async def get_holding(
    ticker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    portfolio = await _get_user_portfolio(user, db)
    detail = await portfolio_service.get_holding_detail(portfolio, ticker, db, redis)
    if not detail:
        raise AppError(
            code="NOT_FOUND",
            message=f"No holding found for ticker '{ticker.upper()}'",
            status_code=404,
        )
    return {"data": detail.model_dump()}


@router.get("/transactions")
async def get_transactions(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    ticker: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    portfolio = await _get_user_portfolio(user, db)
    result = await portfolio_service.get_transactions(
        portfolio.id, db, limit=limit, cursor=cursor, ticker=ticker
    )
    return result.model_dump()


@router.get("/performance")
async def get_performance(
    range: str = Query(default="1M", pattern="^(1W|1M|3M|6M|1Y|ALL)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    portfolio = await _get_user_portfolio(user, db)
    result = await portfolio_service.get_performance_history(
        portfolio, db, redis, range_str=range
    )
    return {"data": result.model_dump()}
