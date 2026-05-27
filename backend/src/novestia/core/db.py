import ssl
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from novestia.config import settings


def _build_engine_args() -> dict[str, Any]:
    """Build engine kwargs, handling sslmode for asyncpg compatibility.

    asyncpg doesn't understand ?sslmode=require in the URL.
    We strip it and pass ssl=True via connect_args instead.
    """
    url = settings.database_url
    connect_args: dict[str, Any] = {}

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    if "sslmode" in params:
        params.pop("sslmode")
        new_query = urlencode(params, doseq=True)
        url = urlunparse(parsed._replace(query=new_query))
        # Create a permissive SSL context for cloud databases
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx

    return {"url": url, "connect_args": connect_args}


_args = _build_engine_args()

engine = create_async_engine(
    _args["url"],
    echo=settings.environment == "development",
    pool_pre_ping=True,
    connect_args=_args["connect_args"],
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an async database session.

    Commits on success, rolls back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
