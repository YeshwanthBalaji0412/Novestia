"""Journal service — standalone entries and trade-linked entries."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.pagination import decode_cursor, encode_cursor
from novestia.models.portfolio import JournalEntry, Transaction


async def list_entries(
    portfolio_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 20,
    cursor: str | None = None,
    entry_type: str | None = None,
) -> dict[str, Any]:
    """Paginated journal entries, newest first."""
    limit = min(max(limit, 1), 100)

    query = (
        select(JournalEntry, Transaction)
        .outerjoin(Transaction, JournalEntry.transaction_id == Transaction.id)
        .where(JournalEntry.portfolio_id == portfolio_id)
    )

    if entry_type == "trade":
        query = query.where(JournalEntry.transaction_id.is_not(None))
    elif entry_type == "reflection":
        query = query.where(JournalEntry.transaction_id.is_(None))

    if cursor:
        cur = decode_cursor(cursor)
        query = query.where(
            (JournalEntry.created_at < cur.timestamp)
            | (
                and_(
                    JournalEntry.created_at == cur.timestamp,
                    JournalEntry.id < cur.id,
                )
            )
        )

    query = query.order_by(
        JournalEntry.created_at.desc(), JournalEntry.id.desc()
    ).limit(limit + 1)

    result = await db.execute(query)
    rows = result.all()

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    items = []
    for entry, txn in rows:
        item: dict[str, Any] = {
            "id": str(entry.id),
            "content": entry.content,
            "transaction_id": str(entry.transaction_id) if entry.transaction_id else None,
            "transaction_summary": None,
            "created_at": entry.created_at.isoformat(),
        }
        if txn:
            item["transaction_summary"] = {
                "ticker": txn.ticker,
                "type": txn.transaction_type,
                "quantity": str(txn.quantity),
                "execution_price": str(txn.execution_price),
            }
        items.append(item)

    next_cursor = None
    if has_more and rows:
        last_entry = rows[-1][0]
        next_cursor = encode_cursor(last_entry.created_at, last_entry.id)

    return {"data": items, "next_cursor": next_cursor}


async def create_entry(
    portfolio_id: uuid.UUID,
    content: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Create a standalone journal entry."""
    entry = JournalEntry(
        portfolio_id=portfolio_id,
        content=content,
    )
    db.add(entry)
    await db.flush()

    return {
        "id": str(entry.id),
        "content": entry.content,
        "transaction_id": None,
        "created_at": entry.created_at.isoformat(),
    }


async def get_entry_count(
    portfolio_id: uuid.UUID,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(JournalEntry)
        .where(JournalEntry.portfolio_id == portfolio_id)
    )
    return result.scalar() or 0
