"""Watchlist CRUD endpoints."""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.auth import get_current_user
from novestia.core.db import get_db
from novestia.core.errors import AppError
from novestia.core.redis import get_redis
from novestia.models.user import User
from novestia.services import watchlist_service

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


@router.get("")
async def list_watchlist(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    items = await watchlist_service.list_items(user.id, db, redis)
    return {"data": [item.model_dump() for item in items]}


@router.post("/{ticker}", status_code=201)
async def add_to_watchlist(
    ticker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    result = await watchlist_service.add_item(user.id, ticker, db, redis)
    return {"data": result.model_dump()}


@router.delete("/{ticker}", status_code=204)
async def remove_from_watchlist(
    ticker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    existed = await watchlist_service.remove_item(user.id, ticker, db)
    if not existed:
        raise AppError(
            code="NOT_FOUND",
            message=f"Ticker '{ticker.upper()}' is not in your watchlist",
            status_code=404,
        )
    return Response(status_code=204)
