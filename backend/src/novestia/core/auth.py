"""FastAPI auth dependencies for Clerk JWT validation.

Two levels:
- get_current_clerk_user: validates JWT, returns ClerkClaims
- get_current_user: resolves Clerk identity to local User row (lazy-creates if missing)
"""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.db import get_db
from novestia.integrations.clerk import (
    AuthenticationError,
    ClerkClaims,
    validate_token,
)
from novestia.models.user import User


def _extract_bearer_token(request: Request) -> str:
    """Extract the Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")
    return auth_header[7:]


async def get_current_clerk_user(request: Request) -> ClerkClaims:
    """Validate the JWT and return Clerk claims. Does not touch the database."""
    token = _extract_bearer_token(request)
    return await validate_token(token)


async def get_current_user(
    claims: ClerkClaims = Depends(get_current_clerk_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve Clerk claims to a local User row.

    If the user doesn't exist yet, creates the row (lazy user creation).
    This means the first authenticated request from a new Clerk user
    automatically creates their local account.
    """
    result = await db.execute(
        select(User).where(User.clerk_user_id == claims.user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            clerk_user_id=claims.user_id,
            email=claims.email,
        )
        db.add(user)
        await db.flush()

    # Update email if it changed in Clerk
    if user.email != claims.email and claims.email:
        user.email = claims.email
        await db.flush()

    return user
