"""Stock service tests with mocked Finnhub and Redis."""

from __future__ import annotations

import json
import time
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.integrations.finnhub import (
    RateLimitExceeded,
    TickerNotFound,
)
from novestia.models.stock import PriceHistory, Stock, StockSnapshot
from novestia.services import stock_service

# ── Fixtures ──


class FakeRedis:
    """Minimal Redis mock for testing."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._counters: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value

    async def incr(self, key: str) -> int:
        self._counters[key] = self._counters.get(key, 0) + 1
        return self._counters[key]

    async def expire(self, key: str, seconds: int) -> None:
        pass


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


def _mock_finnhub_quote() -> dict[str, Any]:
    return {"c": 187.45, "h": 189.0, "l": 186.0, "o": 186.5, "pc": 185.23, "t": int(time.time())}


def _mock_finnhub_profile() -> dict[str, Any]:
    return {
        "name": "Apple Inc",
        "exchange": "NASDAQ",
        "finnhubIndustry": "Technology",
        "currency": "USD",
        "ticker": "AAPL",
    }


def _mock_finnhub_search() -> dict[str, Any]:
    return {
        "result": [
            {
                "symbol": "AAPL", "description": "Apple Inc",
                "type": "Common Stock", "exchange": "NASDAQ",
            },
            {
                "symbol": "AAPX", "description": "Apple Fund",
                "type": "ETP", "exchange": "NYSE",
            },
        ]
    }


def _mock_finnhub_metrics() -> dict[str, Any]:
    return {
        "metric": {
            "peNormalizedAnnual": 31.24,
            "epsNormalizedAnnual": 6.01,
            "beta": 1.24,
            "dividendYieldIndicatedAnnual": 0.52,
            "52WeekHigh": 199.62,
            "52WeekLow": 164.08,
            "marketCapitalization": 2890000.0,
        }
    }


def _mock_finnhub_candles() -> dict[str, Any]:
    now = int(time.time())
    return {
        "s": "ok",
        "c": [180.0, 181.5, 183.0],
        "o": [179.0, 180.0, 181.0],
        "h": [181.0, 182.0, 184.0],
        "l": [178.0, 179.0, 180.5],
        "t": [now - 86400 * 2, now - 86400, now],
        "v": [50000000, 55000000, 48000000],
    }


# ── Search Tests ──


async def test_search_returns_results(
    session: AsyncSession, fake_redis: FakeRedis
) -> None:
    """Search returns results from Finnhub."""
    mock = AsyncMock(return_value=_mock_finnhub_search()["result"])

    import novestia.services.stock_service as svc

    original = svc.finnhub.search_symbols
    svc.finnhub.search_symbols = mock  # type: ignore[assignment]
    try:
        results = await stock_service.search("AAPL", fake_redis, session)
        assert len(results) >= 1
        assert results[0].ticker == "AAPL"
        assert results[0].company_name == "Apple Inc"
    finally:
        svc.finnhub.search_symbols = original  # type: ignore[assignment]


async def test_search_cache_hit(
    session: AsyncSession, fake_redis: FakeRedis
) -> None:
    """Cached search results return without Finnhub call."""
    cache_data = [{
        "ticker": "AAPL", "company_name": "Apple Inc",
        "exchange": "NASDAQ", "instrument_type": "STOCK",
    }]
    await fake_redis.setex("stock:search:AAPL", 3600, json.dumps(cache_data))

    results = await stock_service.search("AAPL", fake_redis, session)
    assert len(results) == 1
    assert results[0].ticker == "AAPL"


# ── Quote Tests ──


async def test_get_quote_fetches_and_caches(
    session: AsyncSession, fake_redis: FakeRedis
) -> None:
    """Quote fetches from Finnhub, caches result, and creates stock row."""
    mock_quote = AsyncMock(return_value={
        "c": Decimal("187.4500"),
        "h": Decimal("189.0000"),
        "l": Decimal("186.0000"),
        "o": Decimal("186.5000"),
        "pc": Decimal("185.2300"),
        "t": int(time.time()),
    })
    mock_profile = AsyncMock(return_value=_mock_finnhub_profile())
    mock_metrics = AsyncMock(return_value=_mock_finnhub_metrics()["metric"])

    import novestia.services.stock_service as svc

    orig_quote = svc.finnhub.get_quote
    orig_profile = svc.finnhub.get_company_profile
    orig_metrics = svc.finnhub.get_basic_financials
    svc.finnhub.get_quote = mock_quote  # type: ignore[assignment]
    svc.finnhub.get_company_profile = mock_profile  # type: ignore[assignment]
    svc.finnhub.get_basic_financials = mock_metrics  # type: ignore[assignment]

    try:
        quote = await stock_service.get_quote("AAPL", fake_redis, session)
        assert quote.ticker == "AAPL"
        assert quote.price == "187.4500"
        assert quote.previous_close == "185.2300"

        # Verify cached
        cached = await fake_redis.get("stock:quote:AAPL")
        assert cached is not None

        # Verify stock row created
        result = await session.execute(select(Stock).where(Stock.ticker == "AAPL"))
        stock = result.scalar_one()
        assert stock.company_name == "Apple Inc"

        # Verify snapshot updated
        result = await session.execute(select(StockSnapshot).where(StockSnapshot.ticker == "AAPL"))
        snapshot = result.scalar_one()
        assert snapshot.last_price == Decimal("187.4500")
    finally:
        svc.finnhub.get_quote = orig_quote  # type: ignore[assignment]
        svc.finnhub.get_company_profile = orig_profile  # type: ignore[assignment]
        svc.finnhub.get_basic_financials = orig_metrics  # type: ignore[assignment]


async def test_get_quote_cache_hit(
    session: AsyncSession, fake_redis: FakeRedis
) -> None:
    """Cached quote returns without Finnhub call."""
    cache_data = {
        "ticker": "MSFT",
        "price": "420.0000",
        "previous_close": "418.0000",
        "change": "2.0000",
        "change_pct": "0.48",
        "market_open": True,
        "stale": False,
        "updated_at": "2026-05-25T12:00:00+00:00",
    }
    await fake_redis.setex("stock:quote:MSFT", 5, json.dumps(cache_data))

    quote = await stock_service.get_quote("MSFT", fake_redis, session)
    assert quote.ticker == "MSFT"
    assert quote.price == "420.0000"


# ── Ticker Not Found Tests ──


async def test_invalid_ticker_raises_404(
    session: AsyncSession, fake_redis: FakeRedis
) -> None:
    """Invalid ticker raises TickerNotFound (404)."""
    mock_quote = AsyncMock(side_effect=TickerNotFound("XXXYZ"))

    import novestia.services.stock_service as svc

    orig = svc.finnhub.get_quote
    svc.finnhub.get_quote = mock_quote  # type: ignore[assignment]
    try:
        with pytest.raises(TickerNotFound):
            await stock_service.get_quote("XXXYZ", fake_redis, session)
    finally:
        svc.finnhub.get_quote = orig  # type: ignore[assignment]


# ── Rate Limit Tests ──


async def test_rate_limit_raises_429(
    session: AsyncSession, fake_redis: FakeRedis
) -> None:
    """Exceeding rate limit raises RateLimitExceeded."""
    # Simulate hitting the rate limit
    fake_redis._counters["finnhub:rate_limit"] = 55

    mock_quote = AsyncMock(return_value={
        "c": Decimal("100"), "h": Decimal("101"), "l": Decimal("99"),
        "o": Decimal("100"), "pc": Decimal("99"), "t": 0,
    })

    import novestia.services.stock_service as svc

    orig = svc.finnhub.get_quote
    svc.finnhub.get_quote = mock_quote  # type: ignore[assignment]
    try:
        # The next call to finnhub._request will check rate limit via the real function
        # But since we mock at the service level, let's test the rate limit directly
        from novestia.integrations.finnhub import _check_rate_limit

        with pytest.raises(RateLimitExceeded):
            await _check_rate_limit(fake_redis)
    finally:
        svc.finnhub.get_quote = orig  # type: ignore[assignment]


# ── Snapshot Tests ──


async def test_snapshot_stores_financials(
    session: AsyncSession, fake_redis: FakeRedis
) -> None:
    """Snapshot refresh stores financial metrics from Finnhub."""
    # First create the stock row
    stock = Stock(
        ticker="GOOG",
        company_name="Alphabet Inc",
        instrument_type="STOCK",
        currency="USD",
    )
    session.add(stock)
    await session.flush()

    mock_metrics = AsyncMock(return_value=_mock_finnhub_metrics()["metric"])

    import novestia.services.stock_service as svc

    orig = svc.finnhub.get_basic_financials
    svc.finnhub.get_basic_financials = mock_metrics  # type: ignore[assignment]
    try:
        await stock_service.refresh_snapshot("GOOG", fake_redis, session)

        result = await session.execute(
            select(StockSnapshot).where(StockSnapshot.ticker == "GOOG")
        )
        snapshot = result.scalar_one()
        assert snapshot.beta == Decimal("1.24")
        assert snapshot.pe_ratio == Decimal("31.24")
        assert snapshot.market_cap == 2890000000000
    finally:
        svc.finnhub.get_basic_financials = orig  # type: ignore[assignment]


# ── History Tests ──


async def test_history_stores_price_data(
    session: AsyncSession, fake_redis: FakeRedis
) -> None:
    """History endpoint fetches candles and stores in price_history."""
    # Create stock row first
    stock = Stock(
        ticker="TSLA",
        company_name="Tesla Inc",
        instrument_type="STOCK",
        currency="USD",
    )
    session.add(stock)
    await session.flush()

    mock_candles = AsyncMock(return_value=_mock_finnhub_candles())
    mock_ensure = AsyncMock(return_value=stock)

    import novestia.services.stock_service as svc

    orig_candles = svc.finnhub.get_candles
    orig_ensure = svc.ensure_stock_exists
    svc.finnhub.get_candles = mock_candles  # type: ignore[assignment]
    svc.ensure_stock_exists = mock_ensure  # type: ignore[assignment]

    try:
        history = await stock_service.get_history(
            "TSLA", "1M", None, fake_redis, session
        )
        assert history.ticker == "TSLA"
        assert len(history.points) == 3
        assert history.interval == "1d"

        # Verify stored in DB
        result = await session.execute(
            select(PriceHistory).where(PriceHistory.ticker == "TSLA")
        )
        rows = result.scalars().all()
        assert len(rows) == 3
    finally:
        svc.finnhub.get_candles = orig_candles  # type: ignore[assignment]
        svc.ensure_stock_exists = orig_ensure  # type: ignore[assignment]


# ── Integration Test (gated by env var) ──


@pytest.mark.skipif(
    not __import__("os").environ.get("FINNHUB_INTEGRATION_TEST"),
    reason="Set FINNHUB_INTEGRATION_TEST=1 to run",
)
async def test_real_finnhub_quote(
    session: AsyncSession, fake_redis: FakeRedis
) -> None:
    """Hit real Finnhub API for AAPL quote. Requires FINNHUB_API_KEY."""
    quote = await stock_service.get_quote("AAPL", fake_redis, session)
    assert quote.ticker == "AAPL"
    assert Decimal(quote.price) > 0
