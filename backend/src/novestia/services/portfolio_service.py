"""Portfolio read service — dashboard summary, holdings, transactions, performance."""

from __future__ import annotations

import json
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.pagination import decode_cursor, encode_cursor
from novestia.models.portfolio import Holding, Portfolio, Transaction
from novestia.models.stock import Stock, StockSnapshot
from novestia.schemas.portfolio import (
    HoldingDetailResponse,
    HoldingSummary,
    PaginatedTransactionsResponse,
    PerformancePoint,
    PerformanceResponse,
    PortfolioSummaryResponse,
    TransactionResponse,
)

ZERO = Decimal("0")
FOUR = Decimal("0.0001")
TWO = Decimal("0.01")


def _fmt4(v: Decimal) -> str:
    return str(v.quantize(FOUR, rounding=ROUND_HALF_UP))


def _fmt2(v: Decimal) -> str:
    return str(v.quantize(TWO, rounding=ROUND_HALF_UP))


async def _get_price(
    ticker: str, redis: Any, snapshot: StockSnapshot | None
) -> tuple[Decimal, Decimal]:
    """Get (current_price, previous_close) from Redis cache or snapshot."""
    cached = await redis.get(f"price:{ticker}")
    if cached:
        data = json.loads(cached)
        return (
            Decimal(str(data.get("price", "0"))),
            Decimal(str(data.get("previous_close", "0"))),
        )
    if snapshot and snapshot.last_price:
        return (
            snapshot.last_price,
            snapshot.previous_close or snapshot.last_price,
        )
    return (ZERO, ZERO)


async def get_portfolio_summary(
    portfolio: Portfolio,
    db: AsyncSession,
    redis: Any,
) -> PortfolioSummaryResponse:
    """Build the full dashboard summary with current prices."""
    # Load holdings with stock info
    result = await db.execute(
        select(Holding, Stock, StockSnapshot)
        .outerjoin(Stock, Holding.ticker == Stock.ticker)
        .outerjoin(StockSnapshot, Holding.ticker == StockSnapshot.ticker)
        .where(Holding.portfolio_id == portfolio.id)
        .where(Holding.quantity > 0)
    )
    rows = result.all()

    invested_value = ZERO
    daily_change_total = ZERO
    holdings: list[HoldingSummary] = []

    for holding, stock, snapshot in rows:
        price, prev_close = await _get_price(holding.ticker, redis, snapshot)

        market_value = holding.quantity * price
        unrealized_pnl = market_value - holding.total_cost
        unrealized_pnl_pct = (
            (unrealized_pnl / holding.total_cost * 100)
            if holding.total_cost != 0
            else ZERO
        )

        daily_chg = (price - prev_close) * holding.quantity
        daily_chg_pct = (
            ((price - prev_close) / prev_close * 100)
            if prev_close != 0
            else ZERO
        )

        invested_value += market_value
        daily_change_total += daily_chg

        holdings.append(
            HoldingSummary(
                ticker=holding.ticker,
                company_name=stock.company_name if stock else holding.ticker,
                quantity=str(holding.quantity),
                average_cost=_fmt4(holding.average_cost),
                current_price=_fmt4(price),
                market_value=_fmt4(market_value),
                total_cost=_fmt4(holding.total_cost),
                unrealized_pnl=_fmt4(unrealized_pnl),
                unrealized_pnl_pct=_fmt2(unrealized_pnl_pct),
                daily_change=_fmt4(daily_chg),
                daily_change_pct=_fmt2(daily_chg_pct),
                weight="0.00",  # computed below
                instrument_type=stock.instrument_type if stock else "STOCK",
                sector=stock.sector if stock else None,
            )
        )

    total_value = portfolio.cash_balance + invested_value
    total_return = total_value - portfolio.starting_balance
    total_return_pct = (
        (total_return / portfolio.starting_balance * 100)
        if portfolio.starting_balance != 0
        else ZERO
    )

    # Compute portfolio-level daily change %
    prev_total = total_value - daily_change_total
    daily_change_pct = (
        (daily_change_total / prev_total * 100) if prev_total != 0 else ZERO
    )

    # Compute weights
    for h in holdings:
        if total_value != 0:
            mv = Decimal(h.market_value)
            h.weight = _fmt2(mv / total_value * 100)

    # Sort by weight descending
    holdings.sort(key=lambda h: Decimal(h.market_value), reverse=True)

    return PortfolioSummaryResponse(
        id=portfolio.id,
        name=portfolio.name,
        cash_balance=_fmt4(portfolio.cash_balance),
        total_value=_fmt4(total_value),
        starting_balance=_fmt4(portfolio.starting_balance),
        total_return=_fmt4(total_return),
        total_return_pct=_fmt2(total_return_pct),
        daily_change=_fmt4(daily_change_total),
        daily_change_pct=_fmt2(daily_change_pct),
        holdings=holdings,
        holdings_count=len(holdings),
    )


async def get_holding_detail(
    portfolio: Portfolio,
    ticker: str,
    db: AsyncSession,
    redis: Any,
) -> HoldingDetailResponse | None:
    """Get detail for a single holding with recent transactions."""
    ticker = ticker.upper()

    result = await db.execute(
        select(Holding, Stock, StockSnapshot)
        .outerjoin(Stock, Holding.ticker == Stock.ticker)
        .outerjoin(StockSnapshot, Holding.ticker == StockSnapshot.ticker)
        .where(Holding.portfolio_id == portfolio.id)
        .where(Holding.ticker == ticker)
    )
    row = result.one_or_none()
    if not row:
        return None

    holding, stock, snapshot = row

    price, _prev = await _get_price(ticker, redis, snapshot)
    market_value = holding.quantity * price
    unrealized_pnl = market_value - holding.total_cost
    unrealized_pnl_pct = (
        (unrealized_pnl / holding.total_cost * 100)
        if holding.total_cost != 0
        else ZERO
    )

    # Recent transactions for this ticker
    txn_result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio.id)
        .where(Transaction.ticker == ticker)
        .order_by(Transaction.executed_at.desc())
        .limit(20)
    )
    txns = txn_result.scalars().all()

    return HoldingDetailResponse(
        ticker=ticker,
        company_name=stock.company_name if stock else ticker,
        quantity=str(holding.quantity),
        average_cost=_fmt4(holding.average_cost),
        current_price=_fmt4(price),
        market_value=_fmt4(market_value),
        total_cost=_fmt4(holding.total_cost),
        unrealized_pnl=_fmt4(unrealized_pnl),
        unrealized_pnl_pct=_fmt2(unrealized_pnl_pct),
        first_purchased_at=holding.first_purchased_at,
        recent_transactions=[
            _txn_to_response(t) for t in txns
        ],
    )


async def get_transactions(
    portfolio_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 20,
    cursor: str | None = None,
    ticker: str | None = None,
) -> PaginatedTransactionsResponse:
    """Paginated transaction history, newest first."""
    limit = min(max(limit, 1), 100)

    query = (
        select(Transaction, Stock)
        .outerjoin(Stock, Transaction.ticker == Stock.ticker)
        .where(Transaction.portfolio_id == portfolio_id)
    )

    if ticker:
        query = query.where(Transaction.ticker == ticker.upper())

    if cursor:
        cur = decode_cursor(cursor)
        # Keyset pagination: rows older than the cursor
        query = query.where(
            (Transaction.executed_at < cur.timestamp)
            | (
                and_(
                    Transaction.executed_at == cur.timestamp,
                    Transaction.id < cur.id,
                )
            )
        )

    query = query.order_by(
        Transaction.executed_at.desc(), Transaction.id.desc()
    ).limit(limit + 1)  # fetch one extra to detect next page

    result = await db.execute(query)
    rows = result.all()

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    items = [
        TransactionResponse(
            id=txn.id,
            ticker=txn.ticker,
            company_name=stock.company_name if stock else None,
            type=txn.transaction_type,
            quantity=str(txn.quantity),
            execution_price=_fmt4(txn.execution_price),
            total_amount=_fmt4(txn.total_amount),
            realized_pnl=_fmt4(txn.realized_pnl) if txn.realized_pnl is not None else None,
            executed_after_hours=txn.executed_after_hours,
            journal_note=txn.journal_note,
            executed_at=txn.executed_at,
        )
        for txn, stock in rows
    ]

    next_cursor = None
    if has_more and items:
        last = rows[-1][0]  # last Transaction
        next_cursor = encode_cursor(last.executed_at, last.id)

    return PaginatedTransactionsResponse(data=items, next_cursor=next_cursor)


async def get_performance_history(
    portfolio: Portfolio,
    db: AsyncSession,
    redis: Any,
    range_str: str = "1M",
) -> PerformanceResponse:
    """Portfolio value over time — reads from portfolio_snapshots table.

    For MVP, if no snapshots exist, returns just the current value as a single point.
    """
    from datetime import UTC, datetime, timedelta

    from novestia.models.portfolio import PortfolioSnapshot

    now = datetime.now(UTC)
    range_map = {
        "1W": timedelta(days=7),
        "1M": timedelta(days=30),
        "3M": timedelta(days=90),
        "6M": timedelta(days=180),
        "1Y": timedelta(days=365),
        "ALL": timedelta(days=3650),
    }
    delta = range_map.get(range_str, timedelta(days=30))
    since = now - delta

    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio.id)
        .where(PortfolioSnapshot.recorded_at >= since)
        .order_by(PortfolioSnapshot.recorded_at.asc())
    )
    snapshots = result.scalars().all()

    # Get current value
    summary = await get_portfolio_summary(portfolio, db, redis)
    current_value = Decimal(summary.total_value)
    total_return = current_value - portfolio.starting_balance
    total_return_pct = (
        (total_return / portfolio.starting_balance * 100)
        if portfolio.starting_balance != 0
        else ZERO
    )

    points: list[PerformancePoint] = []
    for snap in snapshots:
        points.append(
            PerformancePoint(
                date=snap.recorded_at.strftime("%Y-%m-%d"),
                value=_fmt4(snap.total_value),
            )
        )

    # Always add today's value as the last point
    points.append(
        PerformancePoint(
            date=now.strftime("%Y-%m-%d"),
            value=_fmt4(current_value),
        )
    )

    return PerformanceResponse(
        starting_balance=_fmt4(portfolio.starting_balance),
        current_value=_fmt4(current_value),
        total_return=_fmt4(total_return),
        total_return_pct=_fmt2(total_return_pct),
        points=points,
    )


def _txn_to_response(txn: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=txn.id,
        ticker=txn.ticker,
        type=txn.transaction_type,
        quantity=str(txn.quantity),
        execution_price=_fmt4(txn.execution_price),
        total_amount=_fmt4(txn.total_amount),
        realized_pnl=_fmt4(txn.realized_pnl) if txn.realized_pnl is not None else None,
        executed_after_hours=txn.executed_after_hours,
        journal_note=txn.journal_note,
        executed_at=txn.executed_at,
    )
