"""User service — sync from Clerk and onboarding logic."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from novestia.models.portfolio import Portfolio
from novestia.models.user import User
from novestia.models.watchlist import Watchlist


async def sync_user_from_clerk(
    db: AsyncSession,
    clerk_user_id: str,
    email: str,
    display_name: str | None = None,
) -> User:
    """Create or update a local user from Clerk claims. Idempotent."""
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            clerk_user_id=clerk_user_id,
            email=email,
            display_name=display_name,
        )
        db.add(user)
        await db.flush()
    else:
        if email and user.email != email:
            user.email = email
        if display_name and user.display_name != display_name:
            user.display_name = display_name
        await db.flush()

    return user


async def onboard_user(
    db: AsyncSession,
    user: User,
    display_name: str | None = None,
) -> tuple[User, Portfolio]:
    """Mark a user as onboarded and create their default portfolio + watchlist.

    Idempotent: if already onboarded, returns existing portfolio.
    """
    if display_name:
        user.display_name = display_name

    # Check if already onboarded (has a portfolio)
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    existing_portfolio = result.scalar_one_or_none()

    if existing_portfolio is not None:
        # Already onboarded — ensure flag is set and return
        if user.onboarded_at is None:
            user.onboarded_at = datetime.now(UTC)
            await db.flush()
        return user, existing_portfolio

    # Create default portfolio
    portfolio = Portfolio(
        user_id=user.id,
        name="Main Portfolio",
        cash_balance=Decimal("10000.0000"),
        starting_balance=Decimal("10000.0000"),
    )
    db.add(portfolio)

    # Create default watchlist
    watchlist = Watchlist(
        user_id=user.id,
        name="My Watchlist",
    )
    db.add(watchlist)

    # Mark onboarded
    user.onboarded_at = datetime.now(UTC)

    await db.flush()
    return user, portfolio


async def get_user_with_portfolio(
    db: AsyncSession, user: User
) -> tuple[User, Portfolio | None]:
    """Load user with their first portfolio eagerly."""
    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.portfolios))
    )
    loaded_user = result.scalar_one()
    first_portfolio = loaded_user.portfolios[0] if loaded_user.portfolios else None
    return loaded_user, first_portfolio
