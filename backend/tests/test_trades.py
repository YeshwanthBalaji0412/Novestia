"""Exhaustive tests for trade execution, cost basis math, and realized P/L.

These test the trade_service functions directly with an in-memory SQLite DB,
mocking only the Finnhub price fetch.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.models.portfolio import Holding, Portfolio, Transaction
from novestia.schemas.trade import TradeRequest
from novestia.services import trade_service
from novestia.services.market_hours import is_market_open

# ── Helpers ──────────────────────────────────────────────────────────────

def _make_request(
    ticker: str = "AAPL",
    trade_type: str = "BUY",
    quantity: str = "1.00000000",
    note: str = "Test trade",
) -> TradeRequest:
    return TradeRequest(
        ticker=ticker, type=trade_type, quantity=quantity, journal_note=note
    )


def _mock_finnhub_quote(price: str):
    """Patch Finnhub get_quote to return a fixed price."""
    quote = {
        "c": Decimal(price),
        "pc": Decimal("100"),
        "h": Decimal(price),
        "l": Decimal(price),
        "o": Decimal(price),
        "t": 0,
    }
    return patch(
        "novestia.services.trade_service.finnhub.get_quote",
        new_callable=AsyncMock,
        return_value=quote,
    )


def _mock_ensure_stock():
    """Patch ensure_stock_exists to do nothing."""
    return patch(
        "novestia.services.trade_service.ensure_stock_exists",
        new_callable=AsyncMock,
    )


class FakeRedis:
    async def get(self, key: str) -> None:
        return None

    async def incr(self, key: str) -> int:
        return 1

    async def expire(self, key: str, s: int) -> None:
        pass


# ── Buy tests ────────────────────────────────────────────────────────────


async def test_buy_creates_holding(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """First buy creates a new holding row."""
    with _mock_finnhub_quote("150.0000"), _mock_ensure_stock():
        result = await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="10"), session, FakeRedis()
        )

    assert result.transaction.type == "BUY"
    assert result.transaction.execution_price == "150.0000"
    assert result.transaction.total_amount == "1500.0000"
    assert result.portfolio_after.cash_balance == "8500.0000"
    assert result.holding_after is not None
    assert result.holding_after.quantity == "10.00000000"
    assert result.holding_after.average_cost == "150.0000"


async def test_buy_second_updates_weighted_avg_cost(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Second buy at different price updates weighted average cost."""
    with _mock_finnhub_quote("100.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="10"), session, FakeRedis()
        )

    with _mock_finnhub_quote("200.0000"), _mock_ensure_stock():
        result = await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="10"), session, FakeRedis()
        )

    # Weighted avg: (10*100 + 10*200) / 20 = 3000/20 = 150.0000
    assert result.holding_after is not None
    assert result.holding_after.quantity == "20.00000000"
    assert result.holding_after.average_cost == "150.0000"

    # Cash: 10000 - 1000 - 2000 = 7000
    assert result.portfolio_after.cash_balance == "7000.0000"


async def test_buy_fractional_shares(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Fractional share quantities are preserved to 8 decimal places."""
    with _mock_finnhub_quote("150.0000"), _mock_ensure_stock():
        result = await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="0.12345678"), session, FakeRedis()
        )

    assert result.holding_after is not None
    assert result.holding_after.quantity == "0.12345678"


async def test_buy_insufficient_cash(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Buy exceeding cash raises InsufficientCash."""
    with (
        _mock_finnhub_quote("10000.0000"),
        _mock_ensure_stock(),
        pytest.raises(trade_service.InsufficientCash),
    ):
        await trade_service.execute_trade(
            sample_portfolio,
            _make_request(quantity="2"),
            session,
            FakeRedis(),
        )


async def test_buy_zero_quantity_rejected(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Zero or negative quantity raises error."""
    from novestia.core.errors import AppError

    with (
        _mock_finnhub_quote("100.0000"),
        _mock_ensure_stock(),
        pytest.raises(AppError, match="greater than zero"),
    ):
        await trade_service.execute_trade(
            sample_portfolio,
            _make_request(quantity="0"),
            session,
            FakeRedis(),
        )


# ── Sell tests ───────────────────────────────────────────────────────────


async def test_sell_partial_reduces_quantity(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Partial sell reduces quantity, avg_cost unchanged."""
    # Buy 10 shares at $100
    with _mock_finnhub_quote("100.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="10"), session, FakeRedis()
        )

    # Sell 3 shares at $120
    with _mock_finnhub_quote("120.0000"), _mock_ensure_stock():
        result = await trade_service.execute_trade(
            sample_portfolio,
            _make_request(trade_type="SELL", quantity="3"),
            session,
            FakeRedis(),
        )

    assert result.holding_after is not None
    assert result.holding_after.quantity == "7.00000000"
    assert result.holding_after.average_cost == "100.0000"  # unchanged on sell

    # Cash: 10000 - 1000 (buy) + 360 (sell) = 9360
    assert result.portfolio_after.cash_balance == "9360.0000"


async def test_sell_realized_pnl_positive(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Realized P/L is correctly computed on sell with profit."""
    with _mock_finnhub_quote("100.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="10"), session, FakeRedis()
        )

    with _mock_finnhub_quote("150.0000"), _mock_ensure_stock():
        result = await trade_service.execute_trade(
            sample_portfolio,
            _make_request(trade_type="SELL", quantity="5"),
            session,
            FakeRedis(),
        )

    # P/L = (150 - 100) * 5 = 250
    assert result.transaction.realized_pnl == "250.0000"


async def test_sell_realized_pnl_negative(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Realized P/L is correctly negative on a loss."""
    with _mock_finnhub_quote("100.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="10"), session, FakeRedis()
        )

    with _mock_finnhub_quote("80.0000"), _mock_ensure_stock():
        result = await trade_service.execute_trade(
            sample_portfolio,
            _make_request(trade_type="SELL", quantity="5"),
            session,
            FakeRedis(),
        )

    # P/L = (80 - 100) * 5 = -100
    assert result.transaction.realized_pnl == "-100.0000"


async def test_sell_all_deletes_holding(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Selling all shares removes the holding row."""
    with _mock_finnhub_quote("100.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="10"), session, FakeRedis()
        )

    with _mock_finnhub_quote("120.0000"), _mock_ensure_stock():
        result = await trade_service.execute_trade(
            sample_portfolio,
            _make_request(trade_type="SELL", quantity="10"),
            session,
            FakeRedis(),
        )

    # Holding is removed
    assert result.holding_after is None

    # Verify in DB
    db_result = await session.execute(
        select(Holding).where(
            Holding.portfolio_id == sample_portfolio.id,
            Holding.ticker == "AAPL",
        )
    )
    assert db_result.scalars().first() is None


async def test_sell_more_than_held_raises(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Selling more than held raises InsufficientShares."""
    with _mock_finnhub_quote("100.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="5"), session, FakeRedis()
        )

    with (
        _mock_finnhub_quote("100.0000"),
        _mock_ensure_stock(),
        pytest.raises(trade_service.InsufficientShares),
    ):
        await trade_service.execute_trade(
            sample_portfolio,
            _make_request(trade_type="SELL", quantity="10"),
            session,
            FakeRedis(),
        )


async def test_sell_without_holding_raises(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Selling a ticker you don't hold raises InsufficientShares."""
    with (
        _mock_finnhub_quote("100.0000"),
        _mock_ensure_stock(),
        pytest.raises(trade_service.InsufficientShares),
    ):
        await trade_service.execute_trade(
            sample_portfolio,
            _make_request(trade_type="SELL", quantity="1"),
            session,
            FakeRedis(),
            )


# ── Cost basis edge cases ────────────────────────────────────────────────


async def test_cost_basis_three_buys_different_prices(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Three buys at different prices and quantities compute correct avg."""
    with _mock_finnhub_quote("100.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="10"), session, FakeRedis()
        )  # cost = 1000

    with _mock_finnhub_quote("150.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="20"), session, FakeRedis()
        )  # cost = 3000

    with _mock_finnhub_quote("200.0000"), _mock_ensure_stock():
        result = await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="10"), session, FakeRedis()
        )  # cost = 2000

    # Total: 40 shares, total cost = 6000, avg = 150.0000
    assert result.holding_after is not None
    assert result.holding_after.quantity == "40.00000000"
    assert result.holding_after.average_cost == "150.0000"


async def test_buy_sell_buy_cost_basis(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Buy→sell→buy: cost basis resets correctly for new position."""
    # Buy 10 @ 100 (avg = 100)
    with _mock_finnhub_quote("100.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="10"), session, FakeRedis()
        )

    # Sell 10 @ 120 (close position)
    with _mock_finnhub_quote("120.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio,
            _make_request(trade_type="SELL", quantity="10"),
            session,
            FakeRedis(),
        )

    # Buy 5 @ 150 (new position, fresh avg)
    with _mock_finnhub_quote("150.0000"), _mock_ensure_stock():
        result = await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="5"), session, FakeRedis()
        )

    assert result.holding_after is not None
    assert result.holding_after.quantity == "5.00000000"
    assert result.holding_after.average_cost == "150.0000"


# ── Transaction recording ────────────────────────────────────────────────


async def test_transaction_row_created(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Each trade creates a transaction row in the DB."""
    with _mock_finnhub_quote("100.0000"), _mock_ensure_stock():
        await trade_service.execute_trade(
            sample_portfolio, _make_request(quantity="5", note="Testing"), session, FakeRedis()
        )

    result = await session.execute(
        select(Transaction).where(Transaction.portfolio_id == sample_portfolio.id)
    )
    txns = result.scalars().all()
    assert len(txns) == 1
    assert txns[0].ticker == "AAPL"
    assert txns[0].transaction_type == "BUY"
    assert txns[0].quantity == Decimal("5")
    assert txns[0].journal_note == "Testing"


async def test_journal_note_required(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Trade request without journal_note fails validation."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TradeRequest(ticker="AAPL", type="BUY", quantity="1", journal_note="")


# ── Market hours ─────────────────────────────────────────────────────────


def test_market_open_weekday_during_hours() -> None:
    """Market is open on weekday during trading hours."""
    from zoneinfo import ZoneInfo

    # Wednesday 11:00 ET
    dt = datetime(2026, 5, 27, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    assert is_market_open(dt) is True


def test_market_closed_weekend() -> None:
    """Market is closed on weekends."""
    from zoneinfo import ZoneInfo

    # Saturday
    dt = datetime(2026, 5, 23, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    assert is_market_open(dt) is False


def test_market_closed_before_open() -> None:
    """Market is closed before 9:30 ET."""
    from zoneinfo import ZoneInfo

    dt = datetime(2026, 5, 27, 9, 0, tzinfo=ZoneInfo("America/New_York"))
    assert is_market_open(dt) is False


def test_market_closed_after_close() -> None:
    """Market is closed at 4:00 PM ET (exactly at close)."""
    from zoneinfo import ZoneInfo

    dt = datetime(2026, 5, 27, 16, 0, tzinfo=ZoneInfo("America/New_York"))
    assert is_market_open(dt) is False


def test_market_closed_holiday() -> None:
    """Market is closed on US holidays."""
    from zoneinfo import ZoneInfo

    # Christmas 2026
    dt = datetime(2026, 12, 25, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    assert is_market_open(dt) is False
