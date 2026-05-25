"""Finnhub REST client with rate limiting and API call logging.

All external calls go through this module. Rate limiting uses a Redis
token bucket (55 calls/min ceiling, safe under Finnhub's 60/min limit).
Every call is logged to the api_call_log table for observability.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

import httpx
import structlog

from novestia.config import settings
from novestia.core.errors import AppError

logger = structlog.stdlib.get_logger()

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
RATE_LIMIT_KEY = "finnhub:rate_limit"
RATE_LIMIT_MAX = 55  # calls per minute (ceiling under 60)
RATE_LIMIT_WINDOW = 60  # seconds


class FinnhubError(AppError):
    """Generic Finnhub API error."""

    def __init__(self, message: str = "Finnhub API error") -> None:
        super().__init__(code="FINNHUB_ERROR", message=message, status_code=502)


class RateLimitExceeded(AppError):
    """Finnhub rate limit hit."""

    def __init__(self) -> None:
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message="Market data rate limit reached. Try again in a moment.",
            status_code=429,
        )


class TickerNotFound(AppError):
    """Ticker not found on Finnhub."""

    def __init__(self, ticker: str) -> None:
        super().__init__(
            code="TICKER_NOT_FOUND",
            message=f"Ticker '{ticker}' not found",
            status_code=404,
        )


async def _check_rate_limit(redis_client: Any) -> None:
    """Check and increment the rate limit counter in Redis."""
    count = await redis_client.incr(RATE_LIMIT_KEY)
    if count == 1:
        await redis_client.expire(RATE_LIMIT_KEY, RATE_LIMIT_WINDOW)
    if count > RATE_LIMIT_MAX:
        raise RateLimitExceeded()


async def _log_api_call(
    db_session: Any,
    endpoint: str,
    status_code: int | None,
    latency_ms: int,
) -> None:
    """Log an API call to the api_call_log table."""
    from novestia.models.system import APICallLog

    log_entry = APICallLog(
        provider="finnhub",
        endpoint=endpoint,
        status_code=status_code,
        latency_ms=latency_ms,
    )
    db_session.add(log_entry)
    # Don't flush here — let the caller's transaction handle it


async def _request(
    endpoint: str,
    params: dict[str, Any],
    redis_client: Any,
    db_session: Any,
) -> dict[str, Any]:
    """Make an authenticated request to Finnhub with rate limiting and logging."""
    await _check_rate_limit(redis_client)

    params["token"] = settings.finnhub_api_key
    url = f"{FINNHUB_BASE_URL}{endpoint}"

    start = time.monotonic()
    status_code: int | None = None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            status_code = response.status_code

        latency_ms = int((time.monotonic() - start) * 1000)
        await _log_api_call(db_session, endpoint, status_code, latency_ms)

        if response.status_code == 429:
            raise RateLimitExceeded()
        if response.status_code != 200:
            raise FinnhubError(f"Finnhub returned {response.status_code}")

        data: dict[str, Any] = response.json()
        return data

    except (httpx.HTTPError, httpx.TimeoutException) as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        await _log_api_call(db_session, endpoint, status_code, latency_ms)
        logger.error("finnhub_request_failed", endpoint=endpoint, error=str(e))
        raise FinnhubError(f"Finnhub request failed: {e}") from e


async def search_symbols(
    query: str,
    redis_client: Any,
    db_session: Any,
) -> list[dict[str, Any]]:
    """Search for stock symbols matching the query."""
    data = await _request("/search", {"q": query}, redis_client, db_session)
    results: list[dict[str, Any]] = data.get("result", [])
    return results


async def get_quote(
    ticker: str,
    redis_client: Any,
    db_session: Any,
) -> dict[str, Decimal]:
    """Get the current quote for a ticker.

    Returns: {c: current, h: high, l: low, o: open, pc: previous_close, t: timestamp}
    """
    data = await _request("/quote", {"symbol": ticker.upper()}, redis_client, db_session)

    # Finnhub returns all zeros for invalid tickers
    if data.get("c", 0) == 0 and data.get("pc", 0) == 0:
        raise TickerNotFound(ticker)

    return {
        "c": Decimal(str(data["c"])),
        "h": Decimal(str(data["h"])),
        "l": Decimal(str(data["l"])),
        "o": Decimal(str(data["o"])),
        "pc": Decimal(str(data["pc"])),
        "t": data["t"],
    }


async def get_company_profile(
    ticker: str,
    redis_client: Any,
    db_session: Any,
) -> dict[str, Any]:
    """Get company profile (name, exchange, sector, etc)."""
    data = await _request(
        "/stock/profile2", {"symbol": ticker.upper()}, redis_client, db_session
    )
    if not data or not data.get("name"):
        raise TickerNotFound(ticker)
    return data


async def get_basic_financials(
    ticker: str,
    redis_client: Any,
    db_session: Any,
) -> dict[str, Any]:
    """Get basic financials (P/E, EPS, beta, market cap, etc)."""
    data = await _request(
        "/stock/metric",
        {"symbol": ticker.upper(), "metric": "all"},
        redis_client,
        db_session,
    )
    result: dict[str, Any] = data.get("metric", {})
    return result


async def get_candles(
    ticker: str,
    resolution: str,
    from_ts: int,
    to_ts: int,
    redis_client: Any,
    db_session: Any,
) -> dict[str, Any]:
    """Get historical candle data.

    resolution: '1', '5', '15', '30', '60', 'D', 'W', 'M'
    from_ts/to_ts: Unix timestamps
    """
    data = await _request(
        "/stock/candle",
        {
            "symbol": ticker.upper(),
            "resolution": resolution,
            "from": from_ts,
            "to": to_ts,
        },
        redis_client,
        db_session,
    )
    if data.get("s") == "no_data":
        return {"c": [], "h": [], "l": [], "o": [], "t": [], "v": []}
    return data
