"""Auth tests — JWT validation and user sync/onboard idempotency.

Uses RSA keys to generate real JWTs and mocks the JWKS endpoint.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.integrations.clerk import (
    AuthenticationError,
    invalidate_jwks_cache,
    validate_token,
)
from novestia.models.portfolio import Portfolio
from novestia.models.user import User
from novestia.models.watchlist import Watchlist
from novestia.services.user_service import onboard_user, sync_user_from_clerk

# ── RSA key pair for test JWT signing ──

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()

# Convert public key to JWK format for the mock JWKS
_public_numbers = _public_key.public_numbers()


def _int_to_base64url(n: int) -> str:
    byte_length = (n.bit_length() + 7) // 8
    return (
        __import__("base64")
        .urlsafe_b64encode(n.to_bytes(byte_length, "big"))
        .rstrip(b"=")
        .decode()
    )


_TEST_KID = "test-key-1"
_MOCK_JWKS: dict[str, Any] = {
    "keys": [
        {
            "kty": "RSA",
            "kid": _TEST_KID,
            "use": "sig",
            "alg": "RS256",
            "n": _int_to_base64url(_public_numbers.n),
            "e": _int_to_base64url(_public_numbers.e),
        }
    ]
}


def _make_token(
    sub: str = "user_test_123",
    email: str = "test@example.com",
    kid: str = _TEST_KID,
    exp_offset: int = 3600,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT for testing."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "email": email,
        "iat": now,
        "exp": now + exp_offset,
        "nbf": now,
    }
    if extra_claims:
        payload.update(extra_claims)

    private_pem = _private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid})


def _mock_fetch_jwks() -> AsyncMock:
    """Return a mock for _fetch_jwks that returns our test JWKS."""
    mock = AsyncMock(return_value=_MOCK_JWKS)
    return mock


# ── JWT Validation Tests ──


@pytest.fixture(autouse=True)
def _clear_jwks_cache() -> None:
    invalidate_jwks_cache()


async def test_valid_token_returns_claims() -> None:
    """A properly signed, non-expired token returns correct claims."""
    token = _make_token(sub="user_abc", email="abc@test.com")

    with patch(
        "novestia.integrations.clerk._fetch_jwks", _mock_fetch_jwks()
    ):
        claims = await validate_token(token)

    assert claims.user_id == "user_abc"
    assert claims.email == "abc@test.com"
    assert claims.raw["sub"] == "user_abc"


async def test_missing_token_raises_401() -> None:
    """Empty token raises AuthenticationError."""
    with pytest.raises(AuthenticationError, match="No token provided"):
        await validate_token("")


async def test_expired_token_raises_401() -> None:
    """An expired token raises AuthenticationError."""
    token = _make_token(exp_offset=-3600)  # expired 1 hour ago

    with patch(
        "novestia.integrations.clerk._fetch_jwks", _mock_fetch_jwks()
    ), pytest.raises(AuthenticationError, match="Invalid token"):
        await validate_token(token)


async def test_tampered_token_raises_401() -> None:
    """A token signed with a different key raises AuthenticationError."""
    # Generate a different key pair
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    now = int(time.time())
    token = jwt.encode(
        {"sub": "user_x", "email": "x@test.com", "iat": now, "exp": now + 3600},
        other_pem,
        algorithm="RS256",
        headers={"kid": _TEST_KID},
    )

    with patch(
        "novestia.integrations.clerk._fetch_jwks", _mock_fetch_jwks()
    ), pytest.raises(AuthenticationError, match="Invalid token"):
        await validate_token(token)


async def test_unknown_kid_raises_401() -> None:
    """A token with an unknown kid raises AuthenticationError."""
    token = _make_token(kid="unknown-kid-xyz")

    with patch(
        "novestia.integrations.clerk._fetch_jwks", _mock_fetch_jwks()
    ), pytest.raises(AuthenticationError, match="Token signing key not found"):
        await validate_token(token)


async def test_token_missing_sub_raises_401() -> None:
    """A token without a 'sub' claim raises AuthenticationError."""
    now = int(time.time())
    private_pem = _private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    token = jwt.encode(
        {"email": "no-sub@test.com", "iat": now, "exp": now + 3600},
        private_pem,
        algorithm="RS256",
        headers={"kid": _TEST_KID},
    )

    with patch(
        "novestia.integrations.clerk._fetch_jwks", _mock_fetch_jwks()
    ), pytest.raises(AuthenticationError, match="Token missing subject"):
        await validate_token(token)


# ── User Sync Tests ──


async def test_sync_creates_user(session: AsyncSession) -> None:
    """sync_user_from_clerk creates a new user row."""
    user = await sync_user_from_clerk(
        session, clerk_user_id="clerk_new_user", email="new@test.com"
    )
    assert user.clerk_user_id == "clerk_new_user"
    assert user.email == "new@test.com"
    assert user.id is not None


async def test_sync_is_idempotent(session: AsyncSession) -> None:
    """Calling sync twice doesn't duplicate the user."""
    user1 = await sync_user_from_clerk(
        session, clerk_user_id="clerk_idem", email="idem@test.com"
    )
    user2 = await sync_user_from_clerk(
        session, clerk_user_id="clerk_idem", email="idem@test.com"
    )
    assert user1.id == user2.id

    # Verify only one row exists
    result = await session.execute(
        select(User).where(User.clerk_user_id == "clerk_idem")
    )
    users = result.scalars().all()
    assert len(users) == 1


async def test_sync_updates_email(session: AsyncSession) -> None:
    """Sync updates the email if it changed in Clerk."""
    user = await sync_user_from_clerk(
        session, clerk_user_id="clerk_email_change", email="old@test.com"
    )
    assert user.email == "old@test.com"

    user2 = await sync_user_from_clerk(
        session, clerk_user_id="clerk_email_change", email="new@test.com"
    )
    assert user2.email == "new@test.com"
    assert user2.id == user.id


# ── Onboarding Tests ──


async def test_onboard_creates_portfolio_and_watchlist(
    session: AsyncSession,
) -> None:
    """Onboarding creates a portfolio with $10k and a watchlist."""
    user = await sync_user_from_clerk(
        session, clerk_user_id="clerk_onboard", email="onboard@test.com"
    )
    user, portfolio = await onboard_user(session, user, display_name="Test")

    assert user.onboarded_at is not None
    assert user.display_name == "Test"
    assert portfolio.cash_balance == Decimal("10000.0000")
    assert portfolio.starting_balance == Decimal("10000.0000")
    assert portfolio.name == "Main Portfolio"
    assert portfolio.user_id == user.id

    # Verify watchlist was also created
    result = await session.execute(
        select(Watchlist).where(Watchlist.user_id == user.id)
    )
    watchlist = result.scalar_one()
    assert watchlist.name == "My Watchlist"


async def test_onboard_is_idempotent(session: AsyncSession) -> None:
    """Calling onboard twice doesn't duplicate the portfolio."""
    user = await sync_user_from_clerk(
        session, clerk_user_id="clerk_onboard_idem", email="oi@test.com"
    )
    _, portfolio1 = await onboard_user(session, user)
    _, portfolio2 = await onboard_user(session, user)

    assert portfolio1.id == portfolio2.id

    # Only one portfolio exists
    result = await session.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    )
    portfolios = result.scalars().all()
    assert len(portfolios) == 1
