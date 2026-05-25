"""WebSocket connection and subscription manager.

Tracks active connections, manages per-connection subscription sets,
and coordinates with the price worker via Redis pub/sub.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections import defaultdict
from typing import Any

import redis.asyncio as aioredis
import structlog
from fastapi import WebSocket

logger = structlog.stdlib.get_logger()


class ConnectionState:
    """State for a single WebSocket connection."""

    def __init__(self, ws: WebSocket, user_id: str) -> None:
        self.ws = ws
        self.user_id = user_id
        self.subscribed_tickers: set[str] = set()
        self.base_tickers: set[str] = set()  # portfolio + watchlist — always subscribed
        self._pubsub_task: asyncio.Task[None] | None = None


class WSManager:
    """Manages all active WebSocket connections and their subscriptions."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        self._connections: dict[str, ConnectionState] = {}  # conn_id → state
        # Global refcount: how many connections want each ticker
        self._ticker_refs: dict[str, int] = defaultdict(int)

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(
        self,
        conn_id: str,
        ws: WebSocket,
        user_id: str,
        initial_tickers: set[str],
    ) -> None:
        """Register a new connection and subscribe to initial tickers."""
        state = ConnectionState(ws, user_id)
        state.base_tickers = initial_tickers.copy()
        self._connections[conn_id] = state

        # Subscribe to all initial tickers
        for ticker in initial_tickers:
            await self._add_subscription(conn_id, ticker)

        # Start the Redis listener for this connection
        state._pubsub_task = asyncio.create_task(
            self._redis_listener(conn_id)
        )

        # Send initial status
        await self._send(ws, {
            "type": "status",
            "connected": True,
            "subscribed_tickers": sorted(state.subscribed_tickers),
            "market_open": True,  # simplified for now
        })

        logger.info(
            "ws_client_connected",
            conn_id=conn_id,
            user_id=user_id,
            ticker_count=len(initial_tickers),
        )

    async def disconnect(self, conn_id: str) -> None:
        """Clean up a disconnected client."""
        state = self._connections.get(conn_id)
        if not state:
            return

        # Cancel the Redis listener
        if state._pubsub_task:
            state._pubsub_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await state._pubsub_task

        # Unsubscribe from all tickers
        for ticker in list(state.subscribed_tickers):
            await self._remove_subscription(conn_id, ticker)

        del self._connections[conn_id]
        logger.info("ws_client_disconnected", conn_id=conn_id)

    async def subscribe(self, conn_id: str, tickers: list[str]) -> None:
        """Add tickers to a connection's subscription set."""
        state = self._connections.get(conn_id)
        if not state:
            return

        for ticker in tickers:
            ticker = ticker.upper()
            await self._add_subscription(conn_id, ticker)

        await self._send(state.ws, {
            "type": "status",
            "connected": True,
            "subscribed_tickers": sorted(state.subscribed_tickers),
            "market_open": True,
        })

    async def unsubscribe(self, conn_id: str, tickers: list[str]) -> None:
        """Remove tickers from a connection's subscription set.

        Won't remove base tickers (portfolio + watchlist).
        """
        state = self._connections.get(conn_id)
        if not state:
            return

        for ticker in tickers:
            ticker = ticker.upper()
            # Don't unsubscribe from base tickers
            if ticker in state.base_tickers:
                continue
            await self._remove_subscription(conn_id, ticker)

        await self._send(state.ws, {
            "type": "status",
            "connected": True,
            "subscribed_tickers": sorted(state.subscribed_tickers),
            "market_open": True,
        })

    async def _add_subscription(self, conn_id: str, ticker: str) -> None:
        """Add a ticker subscription for a connection."""
        state = self._connections.get(conn_id)
        if not state or ticker in state.subscribed_tickers:
            return

        state.subscribed_tickers.add(ticker)
        self._ticker_refs[ticker] += 1

        # If this is the first subscriber, tell the worker
        if self._ticker_refs[ticker] == 1:
            await self._redis.publish("worker:subscribe", ticker)

    async def _remove_subscription(self, conn_id: str, ticker: str) -> None:
        """Remove a ticker subscription for a connection."""
        state = self._connections.get(conn_id)
        if not state or ticker not in state.subscribed_tickers:
            return

        state.subscribed_tickers.discard(ticker)
        self._ticker_refs[ticker] = max(0, self._ticker_refs[ticker] - 1)

        # If no one is listening, tell the worker
        if self._ticker_refs[ticker] <= 0:
            await self._redis.publish("worker:unsubscribe", ticker)
            del self._ticker_refs[ticker]

    async def _redis_listener(self, conn_id: str) -> None:
        """Listen on Redis pub/sub channels for this connection's tickers."""
        state = self._connections.get(conn_id)
        if not state:
            return

        pubsub = self._redis.pubsub()

        try:
            while conn_id in self._connections:
                current_tickers = state.subscribed_tickers.copy()
                if not current_tickers:
                    await asyncio.sleep(0.5)
                    continue

                channels = [f"prices:{t}" for t in current_tickers]
                await pubsub.subscribe(*channels)

                try:
                    while conn_id in self._connections:
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True, timeout=1.0
                        )
                        if message and message["type"] == "message":
                            data = message["data"]
                            if isinstance(data, bytes):
                                data = data.decode()
                            price_data = json.loads(data)
                            await self._send(state.ws, {
                                "type": "price",
                                **price_data,
                            })

                        # Check if subscription set changed
                        if state.subscribed_tickers != current_tickers:
                            await pubsub.unsubscribe()
                            break

                        await asyncio.sleep(0.01)
                except Exception:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe()
                await pubsub.aclose()  # type: ignore[no-untyped-call]

    async def _send(self, ws: WebSocket, data: dict[str, Any]) -> None:
        """Send a JSON message to a WebSocket client, swallowing errors."""
        with contextlib.suppress(Exception):
            await ws.send_json(data)
