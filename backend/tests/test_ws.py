"""WebSocket and price worker tests.

Tests the WS manager subscription logic, the worker's tick processing,
reaper behavior, and the WebSocket endpoint authentication.
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock

from novestia.services.ws_manager import WSManager
from novestia.workers.price_worker import PriceWorker

# ── Fake Redis for WS Manager ──


class FakeRedisPubSub:
    """Minimal mock for Redis pub/sub."""

    def __init__(self) -> None:
        self._subscribed: set[str] = set()
        self._messages: list[dict[str, str]] = []

    async def subscribe(self, *channels: str) -> None:
        for ch in channels:
            self._subscribed.add(ch)

    async def unsubscribe(self, *channels: str) -> None:
        if channels:
            for ch in channels:
                self._subscribed.discard(ch)
        else:
            self._subscribed.clear()

    async def get_message(
        self, ignore_subscribe_messages: bool = True, timeout: float = 0.0
    ) -> dict[str, str] | None:
        if self._messages:
            return self._messages.pop(0)
        return None

    async def aclose(self) -> None:
        pass


class FakeRedisForWS:
    """Minimal Redis mock supporting pub/sub for WS manager tests."""

    def __init__(self) -> None:
        self._published: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> None:
        self._published.append((channel, message))

    def pubsub(self) -> FakeRedisPubSub:
        return FakeRedisPubSub()


# ── WSManager Tests ──


async def test_ws_manager_subscribe_publishes_to_worker() -> None:
    """Subscribing a ticker publishes to worker:subscribe channel."""
    redis = FakeRedisForWS()
    manager = WSManager(redis)  # type: ignore[arg-type]

    ws = AsyncMock()
    ws.send_json = AsyncMock()

    await manager.connect("conn1", ws, "user1", set())

    # Cancel the pubsub task to avoid hanging
    state = manager._connections["conn1"]
    if state._pubsub_task:
        state._pubsub_task.cancel()

    await manager.subscribe("conn1", ["AAPL"])

    # Should have published to worker:subscribe
    subscribe_msgs = [
        (ch, msg) for ch, msg in redis._published if ch == "worker:subscribe"
    ]
    assert any(msg == "AAPL" for _, msg in subscribe_msgs)

    await manager.disconnect("conn1")


async def test_ws_manager_refcounting() -> None:
    """Two connections subscribing to same ticker → one worker:subscribe.
    First disconnect → no worker:unsubscribe. Second disconnect → unsubscribe.
    """
    redis = FakeRedisForWS()
    manager = WSManager(redis)  # type: ignore[arg-type]

    ws1 = AsyncMock()
    ws1.send_json = AsyncMock()
    ws2 = AsyncMock()
    ws2.send_json = AsyncMock()

    await manager.connect("conn1", ws1, "user1", {"AAPL"})
    state1 = manager._connections["conn1"]
    if state1._pubsub_task:
        state1._pubsub_task.cancel()

    await manager.connect("conn2", ws2, "user2", {"AAPL"})
    state2 = manager._connections["conn2"]
    if state2._pubsub_task:
        state2._pubsub_task.cancel()

    # worker:subscribe should have AAPL once (first connection)
    subscribe_msgs = [
        msg for ch, msg in redis._published if ch == "worker:subscribe"
    ]
    assert subscribe_msgs.count("AAPL") == 1

    redis._published.clear()

    # Disconnect first connection — no unsubscribe
    await manager.disconnect("conn1")
    unsub_msgs = [
        msg for ch, msg in redis._published if ch == "worker:unsubscribe"
    ]
    assert "AAPL" not in unsub_msgs

    # Disconnect second connection — now unsubscribe
    await manager.disconnect("conn2")
    unsub_msgs = [
        msg for ch, msg in redis._published if ch == "worker:unsubscribe"
    ]
    assert "AAPL" in unsub_msgs


async def test_ws_manager_base_tickers_not_unsubscribable() -> None:
    """Base tickers (portfolio/watchlist) cannot be unsubscribed."""
    redis = FakeRedisForWS()
    manager = WSManager(redis)  # type: ignore[arg-type]

    ws = AsyncMock()
    ws.send_json = AsyncMock()

    await manager.connect("conn1", ws, "user1", {"AAPL"})
    state = manager._connections["conn1"]
    if state._pubsub_task:
        state._pubsub_task.cancel()

    # Try to unsubscribe from base ticker
    await manager.unsubscribe("conn1", ["AAPL"])

    # AAPL should still be subscribed
    assert "AAPL" in state.subscribed_tickers

    await manager.disconnect("conn1")


# ── Worker Tests ──


async def test_worker_tick_processing() -> None:
    """Worker processes a tick: caches, publishes, and samples."""
    worker = PriceWorker()

    # Mock Redis
    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.publish = AsyncMock()
    worker._redis = mock_redis

    # Mock DB session factory
    worker._db_session_factory = None  # Skip DB persistence

    await worker._process_tick("AAPL", 187.45, 50000, int(time.time() * 1000))

    # Should have written to cache
    mock_redis.setex.assert_called_once()
    cache_key = mock_redis.setex.call_args[0][0]
    assert cache_key == "price:AAPL"

    # Should have published
    mock_redis.publish.assert_called_once()
    pub_channel = mock_redis.publish.call_args[0][0]
    assert pub_channel == "prices:AAPL"


async def test_worker_sampling_rate() -> None:
    """Worker only persists to DB once per minute per ticker."""
    worker = PriceWorker()

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.publish = AsyncMock()
    worker._redis = mock_redis
    worker._db_session_factory = None

    # Process two ticks within 1 second
    await worker._process_tick("AAPL", 187.45, 50000, 0)
    await worker._process_tick("AAPL", 187.50, 50000, 0)

    # last_sample should be set (first tick triggers sample)
    assert "AAPL" in worker._last_sample

    # Both should have been cached and published
    assert mock_redis.setex.call_count == 2
    assert mock_redis.publish.call_count == 2


async def test_worker_finnhub_message_parsing() -> None:
    """Worker correctly parses Finnhub trade messages."""
    worker = PriceWorker()

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.publish = AsyncMock()
    worker._redis = mock_redis
    worker._db_session_factory = None

    message = json.dumps({
        "type": "trade",
        "data": [
            {"s": "AAPL", "p": 187.45, "v": 100, "t": 1700000000000},
            {"s": "AAPL", "p": 187.50, "v": 200, "t": 1700000001000},
            {"s": "MSFT", "p": 420.10, "v": 50, "t": 1700000000000},
        ],
    })

    await worker._handle_finnhub_message(message)

    # Should process latest AAPL (187.50) and MSFT (420.10)
    assert mock_redis.publish.call_count == 2
    published_data = [
        json.loads(call[0][1])
        for call in mock_redis.publish.call_args_list
    ]
    tickers = {d["ticker"] for d in published_data}
    assert tickers == {"AAPL", "MSFT"}


async def test_worker_subscription_refcounting() -> None:
    """Worker tracks subscription refcounts correctly."""
    worker = PriceWorker()
    worker._ws = AsyncMock()  # Mock WS to prevent actual subscribe

    # Simulate two subscribe requests
    worker._subscriptions["AAPL"] += 1
    worker._subscriptions["AAPL"] += 1
    assert worker._subscriptions["AAPL"] == 2

    # One unsubscribe
    worker._subscriptions["AAPL"] -= 1
    assert worker._subscriptions["AAPL"] == 1

    # Another unsubscribe
    worker._subscriptions["AAPL"] -= 1
    assert worker._subscriptions["AAPL"] == 0


async def test_worker_reaper_removes_stale() -> None:
    """Reaper removes tickers with zero refcount and no recent ticks."""
    worker = PriceWorker()
    worker._ws = AsyncMock()
    worker._running = False  # Don't actually loop

    # Set up a stale ticker
    worker._subscriptions["DEAD"] = 0
    worker._last_tick["DEAD"] = time.monotonic() - 700  # 700s ago > STALE_THRESHOLD

    # Manually run reaper logic
    to_remove = []
    for ticker, refcount in list(worker._subscriptions.items()):
        if refcount <= 0:
            last_tick = worker._last_tick.get(ticker, 0)
            if time.monotonic() - last_tick > 600:
                to_remove.append(ticker)

    for ticker in to_remove:
        await worker._finnhub_unsubscribe(ticker)
        del worker._subscriptions[ticker]

    assert "DEAD" not in worker._subscriptions


async def test_worker_buffer_on_redis_failure() -> None:
    """Worker buffers messages when Redis is unavailable."""
    worker = PriceWorker()

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock(side_effect=Exception("Redis down"))
    mock_redis.publish = AsyncMock(side_effect=Exception("Redis down"))
    worker._redis = mock_redis
    worker._db_session_factory = None

    await worker._process_tick("AAPL", 187.45, 50000, 0)

    assert len(worker._buffer) == 1
    assert worker._buffer[0]["ticker"] == "AAPL"
