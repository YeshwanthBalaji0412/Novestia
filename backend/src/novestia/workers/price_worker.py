"""Price worker — single Finnhub WebSocket connection with Redis fan-out.

Run as: python -m novestia.workers.price_worker

Architecture:
  Finnhub WS → this worker → Redis cache (per-ticker, 5s TTL)
                            → Redis pub/sub (prices:{ticker} channels)
                            → TimescaleDB (sampled, max 1/min per ticker)

The worker also listens on Redis channel 'worker:subscribe' for dynamic
subscription requests from the API servers.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import signal
import time
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import redis.asyncio as aioredis
import structlog
import websockets
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from novestia.config import settings
from novestia.models.stock import PriceHistory

logger = structlog.stdlib.get_logger()

FINNHUB_WS_URL = "wss://ws.finnhub.io"
PRICE_CACHE_TTL = 5  # seconds
SAMPLE_INTERVAL = 60  # seconds — max 1 DB write per ticker per minute
REAPER_INTERVAL = 300  # 5 minutes
STALE_THRESHOLD = 600  # 10 minutes — reaper unsubscribes after this
RECONNECT_BASE_DELAY = 1.0
RECONNECT_MAX_DELAY = 30.0
BUFFER_MAX_SIZE = 1000


class PriceWorker:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._db_session_factory: async_sessionmaker[AsyncSession] | None = None
        self._subscriptions: dict[str, int] = defaultdict(int)  # ticker → refcount
        self._last_sample: dict[str, float] = {}  # ticker → last DB write timestamp
        self._last_tick: dict[str, float] = {}  # ticker → last received tick
        self._running = True
        self._ws: Any = None
        self._buffer: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Main entry point — connect to everything and run."""
        logger.info("price_worker_starting")

        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)

        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        self._db_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        # Run all tasks concurrently
        await asyncio.gather(
            self._run_finnhub_connection(),
            self._listen_for_subscription_requests(),
            self._run_reaper(),
        )

        await self._cleanup()

    def _handle_shutdown(self) -> None:
        logger.info("price_worker_shutdown_requested")
        self._running = False

    async def _cleanup(self) -> None:
        if self._redis:
            await self._redis.aclose()
        logger.info("price_worker_stopped")

    # ── Finnhub WebSocket Connection ──

    async def _run_finnhub_connection(self) -> None:
        """Connect to Finnhub WS with exponential backoff reconnect."""
        delay = RECONNECT_BASE_DELAY

        while self._running:
            try:
                url = f"{FINNHUB_WS_URL}?token={settings.finnhub_api_key}"
                async with websockets.connect(url) as ws:
                    self._ws = ws
                    delay = RECONNECT_BASE_DELAY
                    logger.info("finnhub_ws_connected")

                    # Resubscribe to all active tickers
                    await self._resubscribe_all()

                    async for message in ws:
                        if not self._running:
                            break
                        await self._handle_finnhub_message(message)

            except websockets.exceptions.ConnectionClosed:
                logger.warning("finnhub_ws_disconnected")
            except Exception as e:
                logger.error("finnhub_ws_error", error=str(e))

            self._ws = None
            if not self._running:
                break

            logger.info("finnhub_ws_reconnecting", delay=delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX_DELAY)

    async def _resubscribe_all(self) -> None:
        """Resubscribe to all tracked tickers after reconnect."""
        if not self._ws:
            return
        for ticker in list(self._subscriptions.keys()):
            if self._subscriptions[ticker] > 0:
                await self._finnhub_subscribe(ticker)

    async def _finnhub_subscribe(self, ticker: str) -> None:
        """Send subscribe message to Finnhub WS."""
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
                logger.info("finnhub_subscribed", ticker=ticker)
            except Exception as e:
                logger.error("finnhub_subscribe_failed", ticker=ticker, error=str(e))

    async def _finnhub_unsubscribe(self, ticker: str) -> None:
        """Send unsubscribe message to Finnhub WS."""
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "unsubscribe", "symbol": ticker}))
                logger.info("finnhub_unsubscribed", ticker=ticker)
            except Exception as e:
                logger.error("finnhub_unsubscribe_failed", ticker=ticker, error=str(e))

    async def _handle_finnhub_message(self, raw: str | bytes) -> None:
        """Process a Finnhub trade message."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        if data.get("type") != "trade":
            return

        trades = data.get("data", [])
        if not trades:
            return

        # Group by ticker, take the last price for each
        latest: dict[str, dict[str, Any]] = {}
        for trade in trades:
            symbol = trade.get("s", "")
            if symbol:
                latest[symbol] = trade

        for ticker, trade in latest.items():
            price = trade.get("p", 0)
            volume = trade.get("v", 0)
            ts = trade.get("t", 0)  # milliseconds
            await self._process_tick(ticker, float(price), int(volume), ts)

    async def _process_tick(
        self, ticker: str, price: float, volume: int, ts_ms: int
    ) -> None:
        """Process a single price tick: cache, publish, maybe persist."""
        now = time.monotonic()
        self._last_tick[ticker] = now

        price_data = json.dumps({
            "ticker": ticker,
            "price": f"{Decimal(str(price)):.4f}",
            "timestamp": datetime.now(UTC).isoformat(),
        })

        try:
            if self._redis:
                # Write to Redis cache
                await self._redis.setex(f"price:{ticker}", PRICE_CACHE_TTL, price_data)
                # Publish to pub/sub channel
                await self._redis.publish(f"prices:{ticker}", price_data)
        except Exception as e:
            # Buffer if Redis is unavailable
            if len(self._buffer) < BUFFER_MAX_SIZE:
                self._buffer.append({"ticker": ticker, "price": price_data})
            logger.error("redis_publish_failed", ticker=ticker, error=str(e))
            return

        # Flush any buffered messages
        if self._buffer and self._redis:
            await self._flush_buffer()

        # Sample for TimescaleDB persistence
        last = self._last_sample.get(ticker, 0)
        if now - last >= SAMPLE_INTERVAL:
            self._last_sample[ticker] = now
            await self._persist_tick(ticker, price, volume)

    async def _flush_buffer(self) -> None:
        """Flush buffered messages to Redis."""
        if not self._redis:
            return
        to_flush = self._buffer[:]
        self._buffer.clear()
        for msg in to_flush:
            with contextlib.suppress(Exception):
                await self._redis.publish(f"prices:{msg['ticker']}", msg["price"])

    async def _persist_tick(self, ticker: str, price: float, volume: int) -> None:
        """Store a sampled price in TimescaleDB."""
        if not self._db_session_factory:
            return
        try:
            async with self._db_session_factory() as session:
                entry = PriceHistory(
                    ticker=ticker,
                    recorded_at=datetime.now(UTC),
                    price=Decimal(str(price)),
                    volume=volume or None,
                    source="live_stream",
                )
                session.add(entry)
                await session.commit()
        except Exception as e:
            logger.error("tick_persist_failed", ticker=ticker, error=str(e))

    # ── Redis Subscription Requests ──

    async def _listen_for_subscription_requests(self) -> None:
        """Listen on Redis for subscription/unsubscription requests from API servers."""
        if not self._redis:
            return

        pubsub = self._redis.pubsub()
        await pubsub.subscribe("worker:subscribe", "worker:unsubscribe")

        try:
            while self._running:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    channel = message["channel"]
                    ticker = message["data"]
                    if isinstance(ticker, bytes):
                        ticker = ticker.decode()

                    if channel == "worker:subscribe":
                        self._subscriptions[ticker] += 1
                        if self._subscriptions[ticker] == 1:
                            await self._finnhub_subscribe(ticker)
                    elif channel == "worker:unsubscribe":
                        self._subscriptions[ticker] = max(
                            0, self._subscriptions[ticker] - 1
                        )
                        # Don't unsubscribe immediately — reaper handles it

                await asyncio.sleep(0.01)
        finally:
            await pubsub.unsubscribe()
            await pubsub.aclose()  # type: ignore[no-untyped-call]

    # ── Reaper ──

    async def _run_reaper(self) -> None:
        """Periodically unsubscribe from tickers nobody is listening to."""
        while self._running:
            await asyncio.sleep(REAPER_INTERVAL)
            if not self._running:
                break

            now = time.monotonic()
            to_remove = []

            for ticker, refcount in list(self._subscriptions.items()):
                if refcount <= 0:
                    last_tick = self._last_tick.get(ticker, 0)
                    if now - last_tick > STALE_THRESHOLD:
                        to_remove.append(ticker)

            for ticker in to_remove:
                await self._finnhub_unsubscribe(ticker)
                del self._subscriptions[ticker]
                self._last_tick.pop(ticker, None)
                self._last_sample.pop(ticker, None)
                logger.info("reaper_unsubscribed", ticker=ticker)


async def main() -> None:
    from novestia.core.logging import setup_logging

    setup_logging()
    worker = PriceWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
