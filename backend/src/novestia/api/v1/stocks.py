"""Stock endpoints — search, quote, snapshot, history."""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.auth import get_current_user
from novestia.core.db import get_db
from novestia.core.redis import get_redis
from novestia.models.user import User
from novestia.schemas.stock import (
    StockHistoryResponse,
    StockQuote,
    StockSearchResult,
    StockSnapshotResponse,
)
from novestia.services import stock_service

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])


@router.get("/search", response_model=dict[str, list[StockSearchResult]])
async def search_stocks(
    q: str = Query(min_length=1, max_length=50),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Search stocks by ticker or company name."""
    results = await stock_service.search(q, redis_client, db)
    return {"data": results}


@router.get("/{ticker}/quote", response_model=dict[str, StockQuote])
async def get_quote(
    ticker: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Get current price quote for a ticker."""
    quote = await stock_service.get_quote(ticker, redis_client, db)
    return {"data": quote}


@router.get("/{ticker}/snapshot", response_model=dict[str, StockSnapshotResponse])
async def get_snapshot(
    ticker: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Get full stock snapshot — company info + financial metrics."""
    snapshot = await stock_service.get_snapshot(ticker, redis_client, db)
    return {"data": snapshot}


@router.get("/{ticker}/history", response_model=dict[str, StockHistoryResponse])
async def get_history(
    ticker: str,
    range: str = Query(default="1M", alias="range"),
    interval: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Get price history for charts."""
    history = await stock_service.get_history(
        ticker, range, interval, redis_client, db
    )
    return {"data": history}
