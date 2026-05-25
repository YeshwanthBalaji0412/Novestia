"""Stock service — search, quote, snapshot, and history with caching."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from novestia.integrations import finnhub
from novestia.integrations.finnhub import TickerNotFound
from novestia.models.stock import PriceHistory, Stock, StockSnapshot
from novestia.schemas.stock import (
    HistoryPoint,
    StockHistoryResponse,
    StockQuote,
    StockSearchResult,
    StockSnapshotResponse,
)
from novestia.services.market_hours import is_market_open

logger = structlog.stdlib.get_logger()

QUOTE_CACHE_TTL = 5  # seconds
SEARCH_CACHE_TTL = 3600  # 1 hour
SNAPSHOT_STALE_HOURS = 24

# Range → (resolution, timedelta)
RANGE_CONFIG: dict[str, tuple[str, timedelta]] = {
    "1D": ("5", timedelta(days=1)),
    "1W": ("60", timedelta(weeks=1)),
    "1M": ("D", timedelta(days=30)),
    "3M": ("D", timedelta(days=90)),
    "6M": ("D", timedelta(days=180)),
    "1Y": ("D", timedelta(days=365)),
    "ALL": ("D", timedelta(days=365 * 5)),
}


def _decimal_str(value: Decimal | None) -> str | None:
    """Format Decimal to 4-place string, or None."""
    if value is None:
        return None
    return f"{value:.4f}"


async def search(
    query: str,
    redis_client: Any,
    db: AsyncSession,
) -> list[StockSearchResult]:
    """Search stocks — check local DB first, fall back to Finnhub."""
    query_upper = query.upper().strip()
    if not query_upper:
        return []

    # Check Redis cache
    cache_key = f"stock:search:{query_upper}"
    cached = await redis_client.get(cache_key)
    if cached:
        return [StockSearchResult(**r) for r in json.loads(cached)]

    # Check local DB for exact ticker match
    result = await db.execute(
        select(Stock).where(Stock.ticker == query_upper)
    )
    local_stock = result.scalar_one_or_none()
    if local_stock:
        results = [
            StockSearchResult(
                ticker=local_stock.ticker,
                company_name=local_stock.company_name,
                exchange=local_stock.exchange,
                instrument_type=local_stock.instrument_type,
            )
        ]
        await redis_client.setex(
            cache_key, SEARCH_CACHE_TTL, json.dumps([r.model_dump() for r in results])
        )
        return results

    # Fall back to Finnhub
    raw_results = await finnhub.search_symbols(query_upper, redis_client, db)

    results = []
    for r in raw_results[:10]:
        symbol = r.get("symbol", "")
        # Filter to common stock types
        type_str = r.get("type", "")
        if type_str not in ("Common Stock", "ETP", "ETF", ""):
            continue
        instrument_type = "ETF" if type_str in ("ETP", "ETF") else "STOCK"
        results.append(
            StockSearchResult(
                ticker=symbol,
                company_name=r.get("description", symbol),
                exchange=r.get("exchange"),
                instrument_type=instrument_type,
            )
        )

    if results:
        await redis_client.setex(
            cache_key,
            SEARCH_CACHE_TTL,
            json.dumps([r.model_dump() for r in results]),
        )

    return results


async def get_quote(
    ticker: str,
    redis_client: Any,
    db: AsyncSession,
) -> StockQuote:
    """Get current quote — Redis cache first, then Finnhub."""
    ticker = ticker.upper()
    cache_key = f"stock:quote:{ticker}"

    # Check cache
    cached = await redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        return StockQuote(**data)

    # Fetch from Finnhub
    quote_data = await finnhub.get_quote(ticker, redis_client, db)

    # Ensure stock exists in our DB (backfill on first quote)
    await ensure_stock_exists(ticker, redis_client, db)

    # Update snapshot last_price
    await _update_snapshot_price(
        db, ticker, quote_data["c"], quote_data["pc"]
    )

    current_price = quote_data["c"]
    prev_close = quote_data["pc"]
    change = current_price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else Decimal("0")

    now = datetime.now(UTC)
    result = StockQuote(
        ticker=ticker,
        price=f"{current_price:.4f}",
        previous_close=f"{prev_close:.4f}",
        change=f"{change:.4f}",
        change_pct=f"{change_pct:.2f}",
        market_open=is_market_open(),
        stale=False,
        updated_at=now,
    )

    # Cache for 5 seconds
    await redis_client.setex(
        cache_key, QUOTE_CACHE_TTL, json.dumps(result.model_dump(mode="json"))
    )

    return result


async def _update_snapshot_price(
    db: AsyncSession,
    ticker: str,
    price: Decimal,
    previous_close: Decimal,
) -> None:
    """Update last_price and previous_close in stock_snapshots."""
    result = await db.execute(
        select(StockSnapshot).where(StockSnapshot.ticker == ticker)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot:
        snapshot.last_price = price
        snapshot.previous_close = previous_close
        snapshot.snapshot_taken_at = datetime.now(UTC)
    else:
        snapshot = StockSnapshot(
            ticker=ticker,
            last_price=price,
            previous_close=previous_close,
            snapshot_taken_at=datetime.now(UTC),
        )
        db.add(snapshot)
    await db.flush()


async def ensure_stock_exists(
    ticker: str,
    redis_client: Any,
    db: AsyncSession,
) -> Stock:
    """Ensure a stock row exists. Fetches from Finnhub if not found."""
    ticker = ticker.upper()
    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = result.scalar_one_or_none()

    if stock is not None:
        return stock

    # Fetch profile from Finnhub
    try:
        profile = await finnhub.get_company_profile(ticker, redis_client, db)
    except TickerNotFound:
        # Create a minimal stock entry
        stock = Stock(
            ticker=ticker,
            company_name=ticker,
            instrument_type="STOCK",
            currency="USD",
            metadata_updated_at=datetime.now(UTC),
        )
        db.add(stock)
        await db.flush()
        return stock

    # Determine instrument type from Finnhub's finnhubIndustry field
    instrument_type = "ETF" if profile.get("finnhubIndustry") == "ETF" else "STOCK"

    stock = Stock(
        ticker=ticker,
        company_name=profile.get("name", ticker),
        exchange=profile.get("exchange"),
        sector=profile.get("finnhubIndustry"),
        industry=profile.get("finnhubIndustry"),
        instrument_type=instrument_type,
        currency=profile.get("currency", "USD"),
        metadata_updated_at=datetime.now(UTC),
    )
    db.add(stock)
    await db.flush()

    # Also fetch and store financial metrics
    await refresh_snapshot(ticker, redis_client, db)

    return stock


async def get_snapshot(
    ticker: str,
    redis_client: Any,
    db: AsyncSession,
) -> StockSnapshotResponse:
    """Get full stock snapshot — DB read, triggers refresh if stale."""
    ticker = ticker.upper()
    stock = await ensure_stock_exists(ticker, redis_client, db)

    result = await db.execute(
        select(StockSnapshot).where(StockSnapshot.ticker == ticker)
    )
    snapshot = result.scalar_one_or_none()

    # Trigger background refresh if snapshot is stale or missing
    if snapshot is None or _is_stale(snapshot.snapshot_taken_at):
        await refresh_snapshot(ticker, redis_client, db)
        # Re-read after refresh
        result = await db.execute(
            select(StockSnapshot).where(StockSnapshot.ticker == ticker)
        )
        snapshot = result.scalar_one_or_none()

    return StockSnapshotResponse(
        ticker=stock.ticker,
        company_name=stock.company_name,
        exchange=stock.exchange,
        sector=stock.sector,
        industry=stock.industry,
        instrument_type=stock.instrument_type,
        last_price=_decimal_str(snapshot.last_price) if snapshot else None,
        previous_close=_decimal_str(snapshot.previous_close) if snapshot else None,
        market_cap=snapshot.market_cap if snapshot else None,
        pe_ratio=_decimal_str(snapshot.pe_ratio) if snapshot else None,
        eps=_decimal_str(snapshot.eps) if snapshot else None,
        dividend_yield=_decimal_str(snapshot.dividend_yield) if snapshot else None,
        week_52_high=_decimal_str(snapshot.week_52_high) if snapshot else None,
        week_52_low=_decimal_str(snapshot.week_52_low) if snapshot else None,
        beta=_decimal_str(snapshot.beta) if snapshot else None,
        expense_ratio=_decimal_str(snapshot.expense_ratio) if snapshot else None,
        snapshot_taken_at=snapshot.snapshot_taken_at if snapshot else None,
    )


def _is_stale(taken_at: datetime | None) -> bool:
    """Check if a snapshot is older than SNAPSHOT_STALE_HOURS."""
    if taken_at is None:
        return True
    age = datetime.now(UTC) - taken_at.replace(tzinfo=UTC)
    return age > timedelta(hours=SNAPSHOT_STALE_HOURS)


async def refresh_snapshot(
    ticker: str,
    redis_client: Any,
    db: AsyncSession,
) -> None:
    """Refresh stock snapshot from Finnhub financials. Safe to call anytime."""
    ticker = ticker.upper()

    try:
        metrics = await finnhub.get_basic_financials(ticker, redis_client, db)
    except Exception:
        logger.warning("snapshot_refresh_failed", ticker=ticker)
        return

    result = await db.execute(
        select(StockSnapshot).where(StockSnapshot.ticker == ticker)
    )
    snapshot = result.scalar_one_or_none()

    now = datetime.now(UTC)

    def _to_decimal(val: Any) -> Decimal | None:
        if val is None:
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None

    if snapshot is None:
        snapshot = StockSnapshot(ticker=ticker, snapshot_taken_at=now)
        db.add(snapshot)

    snapshot.pe_ratio = _to_decimal(metrics.get("peNormalizedAnnual"))
    snapshot.eps = _to_decimal(metrics.get("epsNormalizedAnnual"))
    snapshot.beta = _to_decimal(metrics.get("beta"))
    snapshot.dividend_yield = _to_decimal(metrics.get("dividendYieldIndicatedAnnual"))
    snapshot.week_52_high = _to_decimal(metrics.get("52WeekHigh"))
    snapshot.week_52_low = _to_decimal(metrics.get("52WeekLow"))
    snapshot.market_cap = (
        int(metrics["marketCapitalization"] * 1_000_000)
        if metrics.get("marketCapitalization")
        else None
    )
    snapshot.snapshot_taken_at = now

    await db.flush()


async def get_history(
    ticker: str,
    range_str: str,
    interval: str | None,
    redis_client: Any,
    db: AsyncSession,
) -> StockHistoryResponse:
    """Get price history — fetch from Finnhub and store in price_history."""
    ticker = ticker.upper()
    range_str = range_str.upper()

    if range_str not in RANGE_CONFIG:
        range_str = "1M"

    resolution, delta = RANGE_CONFIG[range_str]
    if interval:
        # Map user-facing intervals to Finnhub resolutions
        interval_map = {"5min": "5", "1h": "60", "1d": "D"}
        resolution = interval_map.get(interval, resolution)

    now_ts = int(time.time())
    from_ts = int((datetime.now(UTC) - delta).timestamp())

    # Fetch candles from Finnhub
    await ensure_stock_exists(ticker, redis_client, db)
    candles = await finnhub.get_candles(
        ticker, resolution, from_ts, now_ts, redis_client, db
    )

    points: list[HistoryPoint] = []
    timestamps = candles.get("t", [])
    closes = candles.get("c", [])
    opens = candles.get("o", [])
    highs = candles.get("h", [])
    lows = candles.get("l", [])
    volumes = candles.get("v", [])

    for i in range(len(timestamps)):
        ts = timestamps[i]
        dt = datetime.fromtimestamp(ts, tz=UTC)
        points.append(
            HistoryPoint(
                timestamp=dt,
                open=f"{Decimal(str(opens[i])):.4f}",
                high=f"{Decimal(str(highs[i])):.4f}",
                low=f"{Decimal(str(lows[i])):.4f}",
                close=f"{Decimal(str(closes[i])):.4f}",
                volume=volumes[i] if i < len(volumes) else None,
            )
        )

    # Store in price_history (batch insert, skip duplicates)
    if points:
        await _store_price_history(db, ticker, points, resolution)

    actual_interval = {"5": "5min", "60": "1h", "D": "1d"}.get(resolution, "1d")
    return StockHistoryResponse(
        ticker=ticker,
        range=range_str,
        interval=actual_interval,
        points=points,
    )


async def _store_price_history(
    db: AsyncSession,
    ticker: str,
    points: list[HistoryPoint],
    resolution: str,
) -> None:
    """Store price history points, ignoring duplicates."""
    source = "rest_candle"

    for point in points:
        # Check if already exists
        result = await db.execute(
            select(PriceHistory).where(
                PriceHistory.ticker == ticker,
                PriceHistory.recorded_at == point.timestamp,
            )
        )
        if result.scalar_one_or_none() is None:
            entry = PriceHistory(
                ticker=ticker,
                recorded_at=point.timestamp,
                price=Decimal(point.close),
                volume=point.volume,
                source=source,
            )
            db.add(entry)

    await db.flush()
