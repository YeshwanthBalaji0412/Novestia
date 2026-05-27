from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter

from novestia.config import settings

logger = structlog.stdlib.get_logger()

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": settings.version,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready")
async def readiness_check() -> Any:
    """Check DB and Redis connectivity. Used by Railway health checks."""
    from fastapi.responses import JSONResponse
    from sqlalchemy import text

    from novestia.core.db import async_session_factory
    from novestia.core.redis import get_redis_client

    checks: dict[str, str] = {}

    # Check database
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error("readiness_db_failed", error=str(e))
        checks["database"] = "failed"

    # Check Redis
    try:
        redis = get_redis_client()
        await redis.set("__health__", "1", ex=5)
        checks["redis"] = "ok"
    except Exception as e:
        logger.error("readiness_redis_failed", error=str(e))
        checks["redis"] = "failed"

    all_ok = all(v == "ok" for v in checks.values())

    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ok" if all_ok else "degraded",
            "checks": checks,
            "version": settings.version,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
