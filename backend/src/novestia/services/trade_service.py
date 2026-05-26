"""Trade execution with atomic transactions and correct cost basis math.

The single most important correctness requirement in the entire project.
All money math uses Decimal. The entire operation (transaction insert,
holding upsert, cash update) runs in a single DB transaction.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.errors import AppError
from novestia.integrations import finnhub
from novestia.models.portfolio import Holding, Portfolio, Transaction
from novestia.schemas.trade import (
    HoldingAfter,
    PortfolioAfter,
    TradePreviewResponse,
    TradeRequest,
    TradeResponse,
    TradeWarning,
    TransactionResult,
)
from novestia.services.market_hours import is_market_open
from novestia.services.stock_service import ensure_stock_exists

FOUR = Decimal("0.0001")
EIGHT = Decimal("0.00000001")


def _fmt4(v: Decimal) -> str:
    return str(v.quantize(FOUR, rounding=ROUND_HALF_UP))


def _fmt8(v: Decimal) -> str:
    return str(v.quantize(EIGHT, rounding=ROUND_HALF_UP))


class InsufficientCash(AppError):
    def __init__(self, required: Decimal, available: Decimal) -> None:
        super().__init__(
            code="INSUFFICIENT_CASH",
            message=f"This trade costs ${_fmt4(required)} but you only have ${_fmt4(available)}",
            status_code=422,
            details={"required": _fmt4(required), "available": _fmt4(available)},
        )


class InsufficientShares(AppError):
    def __init__(self, ticker: str, held: Decimal, requested: Decimal) -> None:
        super().__init__(
            code="INSUFFICIENT_SHARES",
            message=(
                f"You only hold {_fmt8(held)} shares of {ticker}"
                f" but tried to sell {_fmt8(requested)}"
            ),
            status_code=422,
            details={"held": _fmt8(held), "requested": _fmt8(requested)},
        )


async def execute_trade(
    portfolio: Portfolio,
    request: TradeRequest,
    db: AsyncSession,
    redis: Any,
) -> TradeResponse:
    """Execute a trade atomically.

    1. Validate ticker exists
    2. Force-fetch live price from Finnhub (bypasses cache)
    3. Determine after-hours flag
    4. Validate cash/shares
    5. Atomic DB transaction: insert txn, upsert holding, update cash
    """
    ticker = request.ticker.upper()
    quantity = Decimal(request.quantity)
    trade_type = request.type

    if quantity <= 0:
        raise AppError(
            code="INVALID_QUANTITY",
            message="Quantity must be greater than zero",
            status_code=422,
        )

    # 1. Ensure stock exists in DB
    await ensure_stock_exists(ticker, redis, db)

    # 2. Force-fetch live price (bypass cache — Decision 1)
    quote = await finnhub.get_quote(ticker, redis, db)
    execution_price = quote["c"]

    # 3. After-hours check
    now = datetime.now(UTC)
    after_hours = not is_market_open(now)

    # 4. Compute total
    total_amount = (quantity * execution_price).quantize(FOUR, rounding=ROUND_HALF_UP)

    # 5. Load existing holding
    result = await db.execute(
        select(Holding).where(
            Holding.portfolio_id == portfolio.id,
            Holding.ticker == ticker,
        )
    )
    holding = result.scalars().first()

    realized_pnl: Decimal | None = None
    holding_after: HoldingAfter | None = None

    if trade_type == "BUY":
        # Validate cash
        if total_amount > portfolio.cash_balance:
            raise InsufficientCash(required=total_amount, available=portfolio.cash_balance)

        # Update or create holding
        if holding:
            # Weighted average cost basis
            old_total = holding.quantity * holding.average_cost
            new_total = old_total + total_amount
            new_quantity = holding.quantity + quantity
            new_avg_cost = (new_total / new_quantity).quantize(
                FOUR, rounding=ROUND_HALF_UP
            )

            holding.quantity = new_quantity
            holding.average_cost = new_avg_cost
            holding.total_cost = (new_quantity * new_avg_cost).quantize(
                FOUR, rounding=ROUND_HALF_UP
            )
            holding.last_updated_at = now
        else:
            holding = Holding(
                portfolio_id=portfolio.id,
                ticker=ticker,
                quantity=quantity,
                average_cost=execution_price,
                total_cost=total_amount,
                first_purchased_at=now,
                last_updated_at=now,
            )
            db.add(holding)

        # Deduct cash
        portfolio.cash_balance -= total_amount

        holding_after = HoldingAfter(
            ticker=ticker,
            quantity=_fmt8(holding.quantity),
            average_cost=_fmt4(holding.average_cost),
        )

    elif trade_type == "SELL":
        # Validate shares
        if not holding or holding.quantity <= 0:
            raise InsufficientShares(ticker, Decimal("0"), quantity)
        if quantity > holding.quantity:
            raise InsufficientShares(ticker, holding.quantity, quantity)

        # Compute realized P/L
        realized_pnl = ((execution_price - holding.average_cost) * quantity).quantize(
            FOUR, rounding=ROUND_HALF_UP
        )

        # Update holding
        new_quantity = holding.quantity - quantity
        if new_quantity == 0:
            # Full sell — remove the holding
            await db.delete(holding)
            holding_after = None
        else:
            # Partial sell — avg_cost stays the same
            holding.quantity = new_quantity
            holding.total_cost = (new_quantity * holding.average_cost).quantize(
                FOUR, rounding=ROUND_HALF_UP
            )
            holding.last_updated_at = now
            holding_after = HoldingAfter(
                ticker=ticker,
                quantity=_fmt8(holding.quantity),
                average_cost=_fmt4(holding.average_cost),
            )

        # Add cash
        portfolio.cash_balance += total_amount

    # Insert transaction row
    txn = Transaction(
        portfolio_id=portfolio.id,
        ticker=ticker,
        transaction_type=trade_type,
        quantity=quantity,
        execution_price=execution_price,
        total_amount=total_amount,
        realized_pnl=realized_pnl,
        executed_after_hours=after_hours,
        journal_note=request.journal_note,
        executed_at=now,
    )
    db.add(txn)

    # Flush to get the transaction ID (commit handled by get_db dependency)
    await db.flush()

    # Trigger risk engine recompute
    from novestia.services import risk_service

    risk_report = await risk_service.compute_and_store(portfolio, db, redis)

    return TradeResponse(
        transaction=TransactionResult(
            id=txn.id,
            ticker=ticker,
            type=trade_type,
            quantity=_fmt8(quantity),
            execution_price=_fmt4(execution_price),
            total_amount=_fmt4(total_amount),
            realized_pnl=(
                _fmt4(realized_pnl) if realized_pnl is not None else None
            ),
            executed_after_hours=after_hours,
            journal_note=request.journal_note,
            executed_at=txn.executed_at,
        ),
        portfolio_after=PortfolioAfter(
            cash_balance=_fmt4(portfolio.cash_balance),
        ),
        holding_after=holding_after,
        risk_score_after=risk_report.overall_score,
    )


async def preview_trade(
    portfolio: Portfolio,
    ticker: str,
    trade_type: str,
    quantity_str: str,
    db: AsyncSession,
    redis: Any,
) -> TradePreviewResponse:
    """Preview a trade without executing. Shows estimated outcome and warnings."""
    ticker = ticker.upper()
    quantity = Decimal(quantity_str)

    if quantity <= 0:
        raise AppError(
            code="INVALID_QUANTITY",
            message="Quantity must be greater than zero",
            status_code=422,
        )

    await ensure_stock_exists(ticker, redis, db)

    # Get current price (use cache for preview, not force-fetch)
    from novestia.services.stock_service import get_quote

    quote = await get_quote(ticker, redis, db)
    price = Decimal(quote.price)

    now = datetime.now(UTC)
    market_open = is_market_open(now)
    total = (quantity * price).quantize(FOUR, rounding=ROUND_HALF_UP)

    # Load existing holding
    result = await db.execute(
        select(Holding).where(
            Holding.portfolio_id == portfolio.id,
            Holding.ticker == ticker,
        )
    )
    holding = result.scalars().first()

    warnings: list[TradeWarning] = []
    holding_after: HoldingAfter | None = None
    cash_after = portfolio.cash_balance

    if trade_type == "BUY":
        if total > portfolio.cash_balance:
            warnings.append(
                TradeWarning(
                    code="INSUFFICIENT_CASH",
                    message=(
                        f"You need ${_fmt4(total)} but only have"
                        f" ${_fmt4(portfolio.cash_balance)}"
                    ),
                )
            )
        cash_after = portfolio.cash_balance - total

        if holding:
            old_total = holding.quantity * holding.average_cost
            new_total = old_total + total
            new_qty = holding.quantity + quantity
            new_avg = (new_total / new_qty).quantize(FOUR, rounding=ROUND_HALF_UP)
            holding_after = HoldingAfter(
                ticker=ticker, quantity=_fmt8(new_qty), average_cost=_fmt4(new_avg)
            )
        else:
            holding_after = HoldingAfter(
                ticker=ticker, quantity=_fmt8(quantity), average_cost=_fmt4(price)
            )

        # Concentration warning
        market_value_after = (
            (holding.quantity + quantity if holding else quantity) * price
        )
        # Rough total value estimate
        total_value_est = cash_after + market_value_after
        if total_value_est > 0:
            weight = market_value_after / total_value_est * 100
            if weight > 30:
                warnings.append(
                    TradeWarning(
                        code="HIGH_CONCENTRATION",
                        message=(
                            f"After this trade, {ticker} would be"
                            f" {weight:.0f}% of your portfolio"
                        ),
                    )
                )

    elif trade_type == "SELL":
        if not holding or quantity > holding.quantity:
            held = holding.quantity if holding else Decimal("0")
            warnings.append(
                TradeWarning(
                    code="INSUFFICIENT_SHARES",
                    message=f"You hold {_fmt8(held)} shares but want to sell {_fmt8(quantity)}",
                )
            )
        cash_after = portfolio.cash_balance + total

        if holding:
            remaining = holding.quantity - quantity
            if remaining > 0:
                holding_after = HoldingAfter(
                    ticker=ticker,
                    quantity=_fmt8(remaining),
                    average_cost=_fmt4(holding.average_cost),
                )

    if not market_open:
        warnings.append(
            TradeWarning(
                code="AFTER_HOURS",
                message=(
                    "Market is closed. Trade will execute at the"
                    " displayed price (after-hours simulation)."
                ),
            )
        )

    return TradePreviewResponse(
        ticker=ticker,
        type=trade_type,
        quantity=_fmt8(quantity),
        estimated_price=_fmt4(price),
        estimated_total=_fmt4(total),
        market_open=market_open,
        after_hours=not market_open,
        portfolio_after=PortfolioAfter(cash_balance=_fmt4(cash_after)),
        holding_after=holding_after,
        warnings=warnings,
    )
