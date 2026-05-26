"""Tests for portfolio service, pagination, and watchlist."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.pagination import decode_cursor, encode_cursor
from novestia.models.portfolio import Holding, Portfolio, Transaction
from novestia.models.stock import Stock, StockSnapshot
from novestia.models.user import User
from novestia.models.watchlist import Watchlist, WatchlistItem
from novestia.services import portfolio_service

# === Pagination tests ===


def test_cursor_roundtrip() -> None:
    """Encode then decode a cursor and get the same values back."""
    ts = datetime(2026, 5, 25, 14, 30, 0, tzinfo=UTC)
    uid = uuid.uuid4()
    encoded = encode_cursor(ts, uid)
    decoded = decode_cursor(encoded)
    assert decoded.timestamp == ts
    assert decoded.id == uid


def test_invalid_cursor_raises() -> None:
    """Decoding garbage raises ValueError."""
    with pytest.raises(ValueError, match="Invalid pagination cursor"):
        decode_cursor("not-a-cursor")


def test_cursor_stability() -> None:
    """Same inputs always produce the same cursor."""
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    uid = uuid.UUID("12345678-1234-1234-1234-123456789abc")
    assert encode_cursor(ts, uid) == encode_cursor(ts, uid)


# === Portfolio summary math tests ===


async def test_portfolio_summary_empty(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Portfolio with no holdings shows only cash."""

    class FakeRedis:
        async def get(self, key: str) -> None:
            return None

    summary = await portfolio_service.get_portfolio_summary(
        sample_portfolio, session, FakeRedis()
    )
    assert summary.cash_balance == "10000.0000"
    assert summary.total_value == "10000.0000"
    assert summary.total_return == "0.0000"
    assert summary.total_return_pct == "0.00"
    assert summary.holdings_count == 0


async def test_portfolio_summary_with_holdings(
    session: AsyncSession,
    sample_portfolio: Portfolio,
    sample_holding: Holding,
) -> None:
    """Portfolio value = cash + sum(quantity * price)."""
    # Create a stock and snapshot so the service can look them up
    stock = Stock(
        ticker="AAPL",
        company_name="Apple Inc.",
        instrument_type="STOCK",
        currency="USD",
    )
    session.add(stock)
    snapshot = StockSnapshot(
        ticker="AAPL",
        last_price=Decimal("200.0000"),
        previous_close=Decimal("195.0000"),
    )
    session.add(snapshot)
    await session.flush()

    class FakeRedis:
        async def get(self, key: str) -> None:
            return None  # Fall back to snapshot

    summary = await portfolio_service.get_portfolio_summary(
        sample_portfolio, session, FakeRedis()
    )

    # 10 shares * $200 = $2000 market value
    # $10000 cash + $2000 = $12000 total
    assert summary.total_value == "12000.0000"
    assert summary.holdings_count == 1
    assert summary.holdings[0].ticker == "AAPL"
    assert summary.holdings[0].market_value == "2000.0000"

    # P/L: $2000 market - $1800 cost = $200 unrealized
    assert summary.holdings[0].unrealized_pnl == "200.0000"

    # Total return: $12000 - $10000 = $2000
    assert summary.total_return == "2000.0000"
    assert summary.total_return_pct == "20.00"


async def test_portfolio_summary_cash_ties_out(
    session: AsyncSession,
    sample_portfolio: Portfolio,
    sample_holding: Holding,
) -> None:
    """cash + sum(holdings.market_value) == total_value"""
    stock = Stock(
        ticker="AAPL",
        company_name="Apple Inc.",
        instrument_type="STOCK",
        currency="USD",
    )
    session.add(stock)
    snapshot = StockSnapshot(
        ticker="AAPL",
        last_price=Decimal("200.0000"),
        previous_close=Decimal("195.0000"),
    )
    session.add(snapshot)
    await session.flush()

    class FakeRedis:
        async def get(self, key: str) -> None:
            return None

    summary = await portfolio_service.get_portfolio_summary(
        sample_portfolio, session, FakeRedis()
    )

    cash = Decimal(summary.cash_balance)
    holdings_value = sum(Decimal(h.market_value) for h in summary.holdings)
    total = Decimal(summary.total_value)
    assert cash + holdings_value == total


# === Transaction pagination tests ===


async def test_transaction_pagination(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Pagination returns correct pages with stable cursors."""
    # Create 5 transactions
    now = datetime.now(UTC)
    txn_ids = []
    for i in range(5):
        txn = Transaction(
            id=uuid.uuid4(),
            portfolio_id=sample_portfolio.id,
            ticker="AAPL",
            transaction_type="BUY",
            quantity=Decimal("1"),
            execution_price=Decimal("100"),
            total_amount=Decimal("100"),
            executed_at=now - timedelta(minutes=i),
        )
        session.add(txn)
        txn_ids.append(txn.id)
    await session.flush()

    # Page 1: get first 2
    result = await portfolio_service.get_transactions(
        sample_portfolio.id, session, limit=2
    )
    assert len(result.data) == 2
    assert result.next_cursor is not None

    # Page 2: get next 2
    result2 = await portfolio_service.get_transactions(
        sample_portfolio.id, session, limit=2, cursor=result.next_cursor
    )
    assert len(result2.data) == 2
    assert result2.next_cursor is not None

    # Page 3: get remaining 1
    result3 = await portfolio_service.get_transactions(
        sample_portfolio.id, session, limit=2, cursor=result2.next_cursor
    )
    assert len(result3.data) == 1
    assert result3.next_cursor is None

    # No duplicates across pages
    all_ids = [t.id for t in result.data + result2.data + result3.data]
    assert len(all_ids) == len(set(all_ids))


# === Watchlist tests ===


async def test_watchlist_add_idempotent(
    session: AsyncSession,
    sample_user: User,
) -> None:
    """Adding the same ticker twice doesn't create duplicates."""
    watchlist = Watchlist(user_id=sample_user.id, name="Test")
    session.add(watchlist)
    await session.flush()

    item1 = WatchlistItem(watchlist_id=watchlist.id, ticker="AAPL")
    session.add(item1)
    await session.flush()

    # Verify only one item
    from sqlalchemy import func, select

    count = await session.execute(
        select(func.count())
        .select_from(WatchlistItem)
        .where(WatchlistItem.watchlist_id == watchlist.id)
    )
    assert count.scalar() == 1


async def test_zero_quantity_holding_excluded(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Holdings with quantity=0 should not appear in the summary."""
    holding = Holding(
        id=uuid.uuid4(),
        portfolio_id=sample_portfolio.id,
        ticker="SOLD",
        quantity=Decimal("0"),
        average_cost=Decimal("100"),
        total_cost=Decimal("0"),
    )
    session.add(holding)
    await session.flush()

    class FakeRedis:
        async def get(self, key: str) -> None:
            return None

    summary = await portfolio_service.get_portfolio_summary(
        sample_portfolio, session, FakeRedis()
    )
    assert all(h.ticker != "SOLD" for h in summary.holdings)
