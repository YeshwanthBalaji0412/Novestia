"""Idempotency middleware for trade endpoints.

Checks the Idempotency-Key header. On cache hit, returns the stored response
without re-executing. Keys expire after 24 hours.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.models.idempotency import IdempotencyKey


async def get_cached_response(
    key: str, db: AsyncSession
) -> tuple[int, str] | None:
    """Check if a response is cached for this idempotency key."""
    result = await db.execute(
        select(IdempotencyKey).where(IdempotencyKey.key == key)
    )
    cached = result.scalars().first()
    if cached:
        return (cached.status_code, cached.response_body)
    return None


async def store_response(
    key: str, status_code: int, response_body: dict, db: AsyncSession  # type: ignore[type-arg]
) -> None:
    """Store a response for future idempotency checks."""
    entry = IdempotencyKey(
        key=key,
        status_code=status_code,
        response_body=json.dumps(response_body),
    )
    db.add(entry)
    await db.flush()
