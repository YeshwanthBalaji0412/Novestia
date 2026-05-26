"""Trade execution and preview endpoints."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.auth import get_current_user
from novestia.core.db import get_db
from novestia.core.idempotency import get_cached_response, store_response
from novestia.core.redis import get_redis
from novestia.models.portfolio import Portfolio
from novestia.models.user import User
from novestia.schemas.trade import TradeRequest
from novestia.services import trade_service

router = APIRouter(prefix="/api/v1/trades", tags=["trades"])


async def _get_portfolio(user: User, db: AsyncSession) -> Portfolio:
    from novestia.core.errors import AppError

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


@router.post("", status_code=201)
async def execute_trade(
    request: TradeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JSONResponse:
    # Check idempotency
    if idempotency_key:
        cached = await get_cached_response(idempotency_key, db)
        if cached:
            status_code, body = cached
            return JSONResponse(
                status_code=status_code,
                content=json.loads(body),
            )

    portfolio = await _get_portfolio(user, db)
    result = await trade_service.execute_trade(portfolio, request, db, redis)
    response_body: dict[str, Any] = {"data": result.model_dump(mode="json")}

    # Store for idempotency
    if idempotency_key:
        await store_response(idempotency_key, 201, response_body, db)

    return JSONResponse(status_code=201, content=response_body)


@router.get("/preview")
async def preview_trade(
    ticker: str = Query(),
    type: str = Query(pattern="^(BUY|SELL)$"),
    quantity: str = Query(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    portfolio = await _get_portfolio(user, db)
    result = await trade_service.preview_trade(
        portfolio, ticker, type, quantity, db, redis
    )
    return {"data": result.model_dump(mode="json")}
