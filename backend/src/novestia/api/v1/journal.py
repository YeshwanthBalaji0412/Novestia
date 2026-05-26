"""Journal endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.auth import get_current_user
from novestia.core.db import get_db
from novestia.core.errors import AppError
from novestia.models.portfolio import Portfolio
from novestia.models.user import User
from novestia.services import journal_service

router = APIRouter(prefix="/api/v1/journal", tags=["journal"])


async def _get_portfolio(user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise AppError(code="NOT_FOUND", message="Portfolio not found", status_code=404)
    return portfolio


class CreateJournalRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


@router.get("")
async def list_journal(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    type: str | None = Query(default=None, pattern="^(trade|reflection)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    portfolio = await _get_portfolio(user, db)
    return await journal_service.list_entries(
        portfolio.id, db, limit=limit, cursor=cursor, entry_type=type
    )


@router.post("", status_code=201)
async def create_journal(
    request: CreateJournalRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    portfolio = await _get_portfolio(user, db)
    entry = await journal_service.create_entry(portfolio.id, request.content, db)
    return {"data": entry}
