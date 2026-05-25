"""Test fixtures for database smoke tests.

Uses an async SQLite database for model/relationship tests that don't require
Postgres-specific features. Tests requiring TimescaleDB or Postgres constraints
are marked with @pytest.mark.postgres and skipped by default.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from novestia.models import Base
from novestia.models.portfolio import Holding, Portfolio
from novestia.models.user import User


def _register_sqlite_functions(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
    """Register Postgres-compatible functions for SQLite."""
    dbapi_conn.create_function("now", 0, lambda: datetime.now(UTC).isoformat())


@pytest.fixture
async def engine():
    """Create an async SQLite engine for testing."""
    from sqlalchemy import event

    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    event.listen(eng.sync_engine, "connect", _register_sqlite_functions)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:  # type: ignore[no-untyped-def]
    """Yield an async session bound to the test engine."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def sample_user(session: AsyncSession) -> User:
    """Create and return a sample user."""
    user = User(
        id=uuid.uuid4(),
        clerk_user_id="clerk_test_user_001",
        email="test@novestia.app",
        display_name="Test User",
    )
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
async def sample_portfolio(session: AsyncSession, sample_user: User) -> Portfolio:
    """Create and return a sample portfolio for the sample user."""
    portfolio = Portfolio(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        name="Main Portfolio",
        cash_balance=Decimal("10000.0000"),
        starting_balance=Decimal("10000.0000"),
    )
    session.add(portfolio)
    await session.flush()
    return portfolio


@pytest.fixture
async def sample_holding(
    session: AsyncSession, sample_portfolio: Portfolio
) -> Holding:
    """Create and return a sample holding."""
    holding = Holding(
        id=uuid.uuid4(),
        portfolio_id=sample_portfolio.id,
        ticker="AAPL",
        quantity=Decimal("10.00000000"),
        average_cost=Decimal("180.0000"),
        total_cost=Decimal("1800.0000"),
    )
    session.add(holding)
    await session.flush()
    return holding
