"""Risk score endpoints."""

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
from novestia.schemas.risk import RiskHistoryPoint, RiskReportResponse, SubscoreResponse
from novestia.services import risk_service

router = APIRouter(prefix="/api/v1/portfolio/risk", tags=["risk"])


async def _get_portfolio(user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise AppError(
            code="NOT_FOUND",
            message="Portfolio not found.",
            status_code=404,
        )
    return portfolio


def _report_to_response(report: Any) -> dict[str, Any]:
    return RiskReportResponse(
        id=report.id,
        overall_score=report.overall_score,
        subscores={
            "concentration": SubscoreResponse(
                score=report.concentration_score or 0,
                explanation="",
            ),
            "sector_concentration": SubscoreResponse(
                score=report.sector_concentration_score or 0,
                explanation="",
            ),
            "volatility": SubscoreResponse(
                score=report.volatility_score or 0,
                explanation="",
            ),
            "diversification": SubscoreResponse(
                score=report.diversification_score or 0,
                explanation="",
            ),
            "cash_ratio": SubscoreResponse(
                score=report.cash_ratio_score or 0,
                explanation="",
            ),
        },
        engine_explanation=report.engine_explanation,
        ai_interpretation=report.ai_interpretation,
        computed_at=report.computed_at,
    ).model_dump(mode="json")


@router.get("")
async def get_risk(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    """Get latest risk report. Computes one if none exists."""
    portfolio = await _get_portfolio(user, db)
    report = await risk_service.get_latest(portfolio.id, db)
    if not report:
        report = await risk_service.compute_and_store(portfolio, db, redis)
    return {"data": _report_to_response(report)}


@router.get("/history")
async def get_risk_history(
    limit: int = Query(default=30, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    portfolio = await _get_portfolio(user, db)
    reports = await risk_service.get_history(portfolio.id, db, limit=limit)
    return {
        "data": [
            RiskHistoryPoint(
                overall_score=r.overall_score,
                computed_at=r.computed_at,
            ).model_dump(mode="json")
            for r in reports
        ]
    }


@router.post("/recompute", status_code=201)
async def recompute_risk(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict[str, Any]:
    portfolio = await _get_portfolio(user, db)

    # Rate limit: 1 per minute
    rate_key = f"risk:recompute:{portfolio.id}"
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, 60)
    if count > 1:
        raise AppError(
            code="RATE_LIMITED",
            message="Risk recompute is limited to once per minute.",
            status_code=429,
        )

    report = await risk_service.compute_and_store(portfolio, db, redis)
    return {"data": _report_to_response(report)}
