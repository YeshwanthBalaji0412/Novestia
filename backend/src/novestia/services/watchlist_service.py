"""Watchlist service — add, remove, list with current prices."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.models.stock import Stock
from novestia.models.watchlist import Watchlist, WatchlistItem
from novestia.schemas.watchlist import WatchlistAddResponse, WatchlistItemResponse
from novestia.services.stock_service import ensure_stock_exists, get_quote


async def list_items(
    user_id: Any,
    db: AsyncSession,
    redis: Any,
) -> list[WatchlistItemResponse]:
    """List all watchlist items with current prices."""
    result = await db.execute(
        select(WatchlistItem, Watchlist, Stock)
        .join(Watchlist, WatchlistItem.watchlist_id == Watchlist.id)
        .outerjoin(Stock, WatchlistItem.ticker == Stock.ticker)
        .where(Watchlist.user_id == user_id)
        .order_by(WatchlistItem.added_at.desc())
    )
    rows = result.all()

    items: list[WatchlistItemResponse] = []
    for item, _watchlist, stock in rows:
        # Try Redis cache for price, fall back to snapshot
        price = Decimal("0")
        prev_close = Decimal("0")

        cached = await redis.get(f"price:{item.ticker}")
        if cached:
            data = json.loads(cached)
            price = Decimal(str(data.get("price", "0")))
            prev_close = Decimal(str(data.get("previous_close", "0")))
        else:
            try:
                quote = await get_quote(item.ticker, redis, db)
                price = Decimal(quote.price)
                prev_close = Decimal(quote.previous_close)
            except Exception:
                price = Decimal("0")
                prev_close = Decimal("0")

        change = price - prev_close
        change_pct = (
            (change / prev_close * 100) if prev_close != 0 else Decimal("0")
        )

        items.append(
            WatchlistItemResponse(
                ticker=item.ticker,
                company_name=stock.company_name if stock else item.ticker,
                current_price=f"{price:.4f}",
                previous_close=f"{prev_close:.4f}",
                daily_change=f"{change:.4f}",
                daily_change_pct=f"{change_pct:.2f}",
                added_at=item.added_at,
            )
        )

    return items


async def add_item(
    user_id: Any,
    ticker: str,
    db: AsyncSession,
    redis: Any,
) -> WatchlistAddResponse:
    """Add a ticker to the user's watchlist. Idempotent."""
    ticker = ticker.upper()

    # Ensure stock exists in DB
    await ensure_stock_exists(ticker, redis, db)

    # Get or create the user's watchlist
    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == user_id)
    )
    watchlist = result.scalar_one_or_none()
    if not watchlist:
        watchlist = Watchlist(user_id=user_id, name="My Watchlist")
        db.add(watchlist)
        await db.flush()

    # Check if already in watchlist
    item_result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist.id,
            WatchlistItem.ticker == ticker,
        )
    )
    existing = item_result.scalars().first()
    if existing:
        return WatchlistAddResponse(ticker=ticker, added_at=existing.added_at)

    # Add
    item = WatchlistItem(watchlist_id=watchlist.id, ticker=ticker)
    db.add(item)
    await db.flush()

    # Notify WS worker to subscribe to this ticker
    await redis.publish("worker:subscribe", ticker)

    return WatchlistAddResponse(ticker=ticker, added_at=item.added_at)


async def remove_item(
    user_id: Any,
    ticker: str,
    db: AsyncSession,
) -> bool:
    """Remove a ticker from the watchlist. Returns True if it existed."""
    ticker = ticker.upper()

    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == user_id)
    )
    watchlist = result.scalar_one_or_none()
    if not watchlist:
        return False

    result = await db.execute(
        delete(WatchlistItem)
        .where(
            WatchlistItem.watchlist_id == watchlist.id,
            WatchlistItem.ticker == ticker,
        )
        .returning(WatchlistItem.id)
    )
    deleted = result.scalar_one_or_none()
    return deleted is not None
