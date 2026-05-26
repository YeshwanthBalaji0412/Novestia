"""Risk service — bridges the pure engine with DB persistence."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.models.portfolio import Holding, Portfolio
from novestia.models.risk import RiskReport
from novestia.models.stock import Stock, StockSnapshot
from novestia.services.risk_engine import (
    HoldingInput,
    RiskEngineResult,
    compute_risk_report,
)


async def compute_and_store(
    portfolio: Portfolio,
    db: AsyncSession,
    redis: Any,
) -> RiskReport:
    """Pull portfolio data, run the engine, persist the report."""
    engine_result = await _run_engine(portfolio, db, redis)

    report = RiskReport(
        portfolio_id=portfolio.id,
        overall_score=engine_result.overall_score,
        concentration_score=engine_result.concentration.score,
        sector_concentration_score=engine_result.sector_concentration.score,
        volatility_score=engine_result.volatility.score,
        diversification_score=engine_result.diversification.score,
        cash_ratio_score=engine_result.cash_ratio.score,
        engine_explanation=engine_result.engine_explanation,
    )
    db.add(report)
    await db.flush()
    return report


async def get_latest(
    portfolio_id: Any,
    db: AsyncSession,
) -> RiskReport | None:
    """Get the most recent risk report."""
    result = await db.execute(
        select(RiskReport)
        .where(RiskReport.portfolio_id == portfolio_id)
        .order_by(RiskReport.computed_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def get_history(
    portfolio_id: Any,
    db: AsyncSession,
    limit: int = 30,
) -> list[RiskReport]:
    """Get risk reports over time, newest first."""
    result = await db.execute(
        select(RiskReport)
        .where(RiskReport.portfolio_id == portfolio_id)
        .order_by(RiskReport.computed_at.desc())
        .limit(min(limit, 90))
    )
    return list(result.scalars().all())


async def _run_engine(
    portfolio: Portfolio,
    db: AsyncSession,
    redis: Any,
) -> RiskEngineResult:
    """Gather inputs and call the pure risk engine."""
    import json

    # Load holdings with stock info
    result = await db.execute(
        select(Holding, Stock, StockSnapshot)
        .outerjoin(Stock, Holding.ticker == Stock.ticker)
        .outerjoin(StockSnapshot, Holding.ticker == StockSnapshot.ticker)
        .where(Holding.portfolio_id == portfolio.id)
        .where(Holding.quantity > 0)
    )
    rows = result.all()

    holdings: list[HoldingInput] = []
    invested_value = Decimal("0")

    for holding, stock, snapshot in rows:
        # Get current price from Redis cache or snapshot
        price = Decimal("0")
        cached = await redis.get(f"price:{holding.ticker}")
        if cached:
            data = json.loads(cached)
            price = Decimal(str(data.get("price", "0")))
        elif snapshot and snapshot.last_price:
            price = snapshot.last_price

        market_value = holding.quantity * price
        invested_value += market_value

        holdings.append(
            HoldingInput(
                ticker=holding.ticker,
                quantity=holding.quantity,
                market_value=market_value,
                sector=stock.sector if stock else None,
                instrument_type=(
                    stock.instrument_type if stock else "STOCK"
                ),
                beta=snapshot.beta if snapshot else None,
            )
        )

    total_value = portfolio.cash_balance + invested_value
    return compute_risk_report(holdings, portfolio.cash_balance, total_value)
