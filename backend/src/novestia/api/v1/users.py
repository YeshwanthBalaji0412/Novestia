"""User endpoints — sync, onboard, me."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.core.auth import get_current_clerk_user, get_current_user
from novestia.core.db import get_db
from novestia.core.errors import AppError
from novestia.integrations.clerk import ClerkClaims
from novestia.models.user import User
from novestia.schemas.user import OnboardRequest, OnboardResponse, UserResponse
from novestia.services.user_service import (
    get_user_with_portfolio,
    onboard_user,
    reset_portfolio,
    sync_user_from_clerk,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _user_to_response(user: User, portfolio_id: Any = None) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        onboarded=user.onboarded_at is not None,
        portfolio_id=portfolio_id,
        created_at=user.created_at,
    )


@router.post("/sync", response_model=dict[str, UserResponse])
async def sync_user(
    claims: ClerkClaims = Depends(get_current_clerk_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, UserResponse]:
    """Sync user from Clerk. Called on every frontend login. Idempotent."""
    user = await sync_user_from_clerk(
        db,
        clerk_user_id=claims.user_id,
        email=claims.email,
    )
    _, portfolio = await get_user_with_portfolio(db, user)
    return {"data": _user_to_response(user, portfolio.id if portfolio else None)}


@router.post("/onboard", response_model=dict[str, OnboardResponse], status_code=201)
async def onboard(
    body: OnboardRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, OnboardResponse]:
    """Onboard the user — creates portfolio + watchlist. Idempotent."""
    user, portfolio = await onboard_user(db, user, body.display_name)
    return {
        "data": OnboardResponse(
            user=_user_to_response(user, portfolio.id),
            portfolio_id=portfolio.id,
        )
    }


@router.get("/me", response_model=dict[str, UserResponse])
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, UserResponse]:
    """Return the current authenticated user."""
    _, portfolio = await get_user_with_portfolio(db, user)
    return {"data": _user_to_response(user, portfolio.id if portfolio else None)}


@router.post("/reset-portfolio")
async def reset_user_portfolio(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Reset portfolio to $10k, wipe all trades/holdings/journal."""
    try:
        portfolio = await reset_portfolio(db, user)
    except ValueError as e:
        raise AppError(code="NOT_FOUND", message=str(e), status_code=404) from e
    return {
        "data": {
            "message": "Portfolio reset",
            "cash_balance": str(portfolio.cash_balance),
        }
    }


@router.patch("/me")
async def update_me(
    body: OnboardRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, UserResponse]:
    """Update display name."""
    if body.display_name is not None:
        user.display_name = body.display_name
        await db.flush()
    _, portfolio = await get_user_with_portfolio(db, user)
    return {"data": _user_to_response(user, portfolio.id if portfolio else None)}
