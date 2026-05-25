"""Clerk JWT validation with JWKS key caching.

Fetches Clerk's public JWKS keys, caches them, and validates JWTs
from incoming requests. Raises typed errors for 401/403 mapping.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog
from jose import JWTError, jwt

from novestia.config import settings
from novestia.core.errors import AppError

logger = structlog.stdlib.get_logger()

# JWKS cache: keys and expiry timestamp
_jwks_cache: dict[str, Any] = {}
_jwks_cache_expiry: float = 0.0
_JWKS_CACHE_TTL = 3600  # 1 hour


class AuthenticationError(AppError):
    """Raised when JWT validation fails."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
        )


class AuthorizationError(AppError):
    """Raised when the user lacks permission."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
        )


@dataclass(frozen=True)
class ClerkClaims:
    """Validated claims extracted from a Clerk JWT."""

    user_id: str  # Clerk's user ID (sub claim)
    email: str
    raw: dict[str, Any] = field(repr=False)


async def _fetch_jwks() -> dict[str, Any]:
    """Fetch Clerk's JWKS endpoint and return the key set."""
    global _jwks_cache, _jwks_cache_expiry

    now = time.monotonic()
    if _jwks_cache and now < _jwks_cache_expiry:
        return _jwks_cache

    if not settings.clerk_publishable_key:
        raise AuthenticationError("Clerk is not configured")

    jwks_url = f"https://{_get_clerk_domain()}/.well-known/jwks.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        jwks: dict[str, Any] = response.json()

    _jwks_cache = jwks
    _jwks_cache_expiry = now + _JWKS_CACHE_TTL
    logger.info("jwks_fetched", url=jwks_url, key_count=len(jwks.get("keys", [])))
    return jwks


def _get_clerk_domain() -> str:
    """Extract the Clerk frontend API domain from the publishable key.

    Clerk publishable keys encode the frontend API domain:
    pk_test_<base64(domain)>  or  pk_live_<base64(domain)>
    """
    pk = settings.clerk_publishable_key
    if not pk:
        raise AuthenticationError("Clerk publishable key not configured")

    # Strip the pk_test_ or pk_live_ prefix
    parts = pk.split("_", 2)
    if len(parts) < 3:
        raise AuthenticationError("Invalid Clerk publishable key format")

    encoded = parts[2]
    # Clerk adds a trailing $ to the base64
    if encoded.endswith("$"):
        encoded = encoded[:-1]

    # Add padding if needed
    padding = 4 - len(encoded) % 4
    if padding != 4:
        encoded += "=" * padding

    try:
        domain = base64.b64decode(encoded).decode("utf-8")
    except Exception as exc:
        raise AuthenticationError("Could not decode Clerk publishable key") from exc

    # Clerk encodes a trailing $ in the domain — strip it
    return domain.rstrip("$")


async def validate_token(token: str) -> ClerkClaims:
    """Validate a Clerk JWT and return the extracted claims.

    Raises AuthenticationError on any validation failure.
    """
    if not token:
        raise AuthenticationError("No token provided")

    try:
        jwks = await _fetch_jwks()
    except httpx.HTTPError as e:
        logger.error("jwks_fetch_failed", error=str(e))
        raise AuthenticationError("Could not validate token (JWKS unavailable)") from e

    try:
        # Decode the token header to find the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise AuthenticationError("Token missing key ID")

        # Find the matching key in JWKS
        rsa_key: dict[str, Any] = {}
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if not rsa_key:
            # Key not found — might be rotated, clear cache and retry once
            global _jwks_cache_expiry
            _jwks_cache_expiry = 0.0
            jwks = await _fetch_jwks()
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break

        if not rsa_key:
            raise AuthenticationError("Token signing key not found")

        # Validate the token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,  # Clerk doesn't set aud by default
            },
        )
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}") from e

    # Extract claims
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token missing subject claim")

    # Clerk puts email in different places depending on configuration
    email = (
        payload.get("email")
        or payload.get("email_address")
        or payload.get("primary_email_address", "")
    )

    return ClerkClaims(user_id=user_id, email=email, raw=payload)


def invalidate_jwks_cache() -> None:
    """Force JWKS cache refresh on next validation. Useful for testing."""
    global _jwks_cache, _jwks_cache_expiry
    _jwks_cache = {}
    _jwks_cache_expiry = 0.0
