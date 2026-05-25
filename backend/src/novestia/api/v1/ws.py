"""Authenticated WebSocket endpoint for live price streaming."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from novestia.core.db import async_session_factory
from novestia.core.redis import get_redis_client
from novestia.integrations.clerk import AuthenticationError, validate_token
from novestia.models.portfolio import Portfolio
from novestia.models.user import User
from novestia.models.watchlist import Watchlist
from novestia.services.ws_manager import WSManager

logger = structlog.stdlib.get_logger()

router = APIRouter()

# Global WS manager — initialized lazily
_ws_manager: WSManager | None = None


def _get_ws_manager() -> WSManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WSManager(get_redis_client())
    return _ws_manager


async def _authenticate_ws(ws: WebSocket) -> str | None:
    """Extract and validate JWT from WebSocket query params.

    Returns the Clerk user ID on success, None on failure.
    """
    token = ws.query_params.get("token", "")
    if not token:
        return None
    try:
        claims = await validate_token(token)
        return claims.user_id
    except AuthenticationError:
        return None


async def _get_user_tickers(clerk_user_id: str) -> set[str]:
    """Fetch the user's portfolio holdings + watchlist tickers."""
    tickers: set[str] = set()

    async with async_session_factory() as session:
        # Get user
        result = await session.execute(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return tickers

        # Get portfolio holdings
        result = await session.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user.id)
            .options(selectinload(Portfolio.holdings))
        )
        portfolio = result.scalar_one_or_none()
        if portfolio:
            for holding in portfolio.holdings:  # type: ignore[attr-defined]
                tickers.add(holding.ticker)

        # Get watchlist items
        result = await session.execute(
            select(Watchlist)
            .where(Watchlist.user_id == user.id)
            .options(selectinload(Watchlist.items))
        )
        watchlists = result.scalars().all()
        for watchlist in watchlists:
            for item in watchlist.items:  # type: ignore[attr-defined]
                tickers.add(item.ticker)

    return tickers


@router.websocket("/api/v1/ws/prices")
async def websocket_prices(ws: WebSocket) -> None:
    """Live price streaming over WebSocket.

    Connect: ws://host/api/v1/ws/prices?token=<clerk_jwt>
    Client → Server: {"action": "subscribe", "tickers": ["AAPL"]}
    Client → Server: {"action": "unsubscribe", "tickers": ["AAPL"]}
    Server → Client: {"type": "price", "ticker": "AAPL", "price": "187.45", ...}
    Server → Client: {"type": "status", "subscribed_tickers": [...], ...}
    """
    # Authenticate
    clerk_user_id = await _authenticate_ws(ws)
    if not clerk_user_id:
        await ws.close(code=4001, reason="Authentication required")
        return

    await ws.accept()

    conn_id = str(uuid.uuid4())
    manager = _get_ws_manager()

    # Get the user's tickers for initial subscription
    initial_tickers = await _get_user_tickers(clerk_user_id)

    await manager.connect(conn_id, ws, clerk_user_id, initial_tickers)

    try:
        while True:
            data: dict[str, Any] = await ws.receive_json()
            action = data.get("action", "")

            if action == "subscribe":
                tickers = data.get("tickers", [])
                if isinstance(tickers, list):
                    await manager.subscribe(conn_id, tickers)

            elif action == "unsubscribe":
                tickers = data.get("tickers", [])
                if isinstance(tickers, list):
                    await manager.unsubscribe(conn_id, tickers)

            elif action == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("ws_error", conn_id=conn_id, error=str(e))
    finally:
        await manager.disconnect(conn_id)
