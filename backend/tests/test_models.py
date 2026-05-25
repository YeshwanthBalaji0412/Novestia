"""Smoke tests for SQLAlchemy models — relationships, constraints, types."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.models.portfolio import (
    Holding,
    JournalEntry,
    Portfolio,
    PortfolioSnapshot,
    Transaction,
)
from novestia.models.user import User
from novestia.models.watchlist import Watchlist, WatchlistItem


async def test_user_portfolio_relationship(
    session: AsyncSession,
    sample_user: User,
    sample_portfolio: Portfolio,
) -> None:
    """A user's portfolios are accessible via the relationship."""
    result = await session.execute(
        select(User).where(User.id == sample_user.id)
    )
    user = result.scalar_one()

    await session.refresh(user, ["portfolios"])
    assert len(user.portfolios) == 1
    assert user.portfolios[0].id == sample_portfolio.id
    assert user.portfolios[0].name == "Main Portfolio"


async def test_portfolio_holdings_relationship(
    session: AsyncSession,
    sample_portfolio: Portfolio,
    sample_holding: Holding,
) -> None:
    """A portfolio's holdings are accessible via the relationship."""
    await session.refresh(sample_portfolio, ["holdings"])
    assert len(sample_portfolio.holdings) == 1
    assert sample_portfolio.holdings[0].ticker == "AAPL"
    assert sample_portfolio.holdings[0].quantity == Decimal("10.00000000")


async def test_holding_unique_constraint(
    session: AsyncSession,
    sample_portfolio: Portfolio,
    sample_holding: Holding,
) -> None:
    """Cannot insert two holdings with the same (portfolio_id, ticker)."""
    duplicate = Holding(
        id=uuid.uuid4(),
        portfolio_id=sample_portfolio.id,
        ticker="AAPL",
        quantity=Decimal("5.00000000"),
        average_cost=Decimal("190.0000"),
        total_cost=Decimal("950.0000"),
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_transaction_create_and_relationship(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Can create a transaction and access it via portfolio."""
    txn = Transaction(
        id=uuid.uuid4(),
        portfolio_id=sample_portfolio.id,
        ticker="AAPL",
        transaction_type="BUY",
        quantity=Decimal("5.00000000"),
        execution_price=Decimal("187.4500"),
        total_amount=Decimal("937.2500"),
        executed_after_hours=False,
        journal_note="Test buy",
    )
    session.add(txn)
    await session.flush()

    await session.refresh(sample_portfolio, ["transactions"])
    assert len(sample_portfolio.transactions) == 1
    assert sample_portfolio.transactions[0].ticker == "AAPL"
    assert sample_portfolio.transactions[0].transaction_type == "BUY"


async def test_journal_entry_standalone(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Can create a standalone journal entry (no transaction link)."""
    entry = JournalEntry(
        id=uuid.uuid4(),
        portfolio_id=sample_portfolio.id,
        transaction_id=None,
        content="Weekly reflection on market conditions.",
    )
    session.add(entry)
    await session.flush()

    await session.refresh(sample_portfolio, ["journal_entries"])
    assert len(sample_portfolio.journal_entries) == 1
    assert sample_portfolio.journal_entries[0].transaction_id is None


async def test_journal_entry_linked_to_transaction(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """A journal entry can be linked to a transaction."""
    txn = Transaction(
        id=uuid.uuid4(),
        portfolio_id=sample_portfolio.id,
        ticker="NVDA",
        transaction_type="BUY",
        quantity=Decimal("2.00000000"),
        execution_price=Decimal("687.0000"),
        total_amount=Decimal("1374.0000"),
        executed_after_hours=False,
        journal_note="Buying NVDA",
    )
    session.add(txn)
    await session.flush()

    entry = JournalEntry(
        id=uuid.uuid4(),
        portfolio_id=sample_portfolio.id,
        transaction_id=txn.id,
        content="Bought NVDA because of AI growth thesis.",
    )
    session.add(entry)
    await session.flush()

    await session.refresh(txn, ["journal_entry"])
    assert txn.journal_entry is not None
    assert txn.journal_entry.content.startswith("Bought NVDA")


async def test_watchlist_items(
    session: AsyncSession,
    sample_user: User,
) -> None:
    """Watchlist with items works via relationships."""
    watchlist = Watchlist(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        name="My Watchlist",
    )
    session.add(watchlist)
    await session.flush()

    item = WatchlistItem(
        id=uuid.uuid4(),
        watchlist_id=watchlist.id,
        ticker="NVDA",
    )
    session.add(item)
    await session.flush()

    await session.refresh(watchlist, ["items"])
    assert len(watchlist.items) == 1
    assert watchlist.items[0].ticker == "NVDA"


async def test_watchlist_item_unique_constraint(
    session: AsyncSession,
    sample_user: User,
) -> None:
    """Cannot add the same ticker twice to a watchlist."""
    watchlist = Watchlist(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        name="Test Watchlist",
    )
    session.add(watchlist)
    await session.flush()

    item1 = WatchlistItem(
        id=uuid.uuid4(),
        watchlist_id=watchlist.id,
        ticker="AAPL",
    )
    session.add(item1)
    await session.flush()

    item2 = WatchlistItem(
        id=uuid.uuid4(),
        watchlist_id=watchlist.id,
        ticker="AAPL",
    )
    session.add(item2)
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_portfolio_snapshot(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Can create a portfolio snapshot."""
    snapshot = PortfolioSnapshot(
        id=uuid.uuid4(),
        portfolio_id=sample_portfolio.id,
        total_value=Decimal("10450.0000"),
        cash_balance=Decimal("1200.0000"),
        recorded_at=datetime.now(UTC),
    )
    session.add(snapshot)
    await session.flush()

    await session.refresh(sample_portfolio, ["snapshots"])
    assert len(sample_portfolio.snapshots) == 1
    assert sample_portfolio.snapshots[0].total_value == Decimal("10450.0000")


async def test_numeric_precision(
    session: AsyncSession,
    sample_portfolio: Portfolio,
) -> None:
    """Money columns preserve 4-decimal precision."""
    sample_portfolio.cash_balance = Decimal("9062.7500")
    await session.flush()

    result = await session.execute(
        select(Portfolio).where(Portfolio.id == sample_portfolio.id)
    )
    portfolio = result.scalar_one()
    assert portfolio.cash_balance == Decimal("9062.7500")


async def test_quantity_precision(
    session: AsyncSession,
    sample_holding: Holding,
) -> None:
    """Quantity columns preserve 8-decimal precision for fractional shares."""
    sample_holding.quantity = Decimal("0.12345678")
    await session.flush()

    result = await session.execute(
        select(Holding).where(Holding.id == sample_holding.id)
    )
    holding = result.scalar_one()
    assert holding.quantity == Decimal("0.12345678")
