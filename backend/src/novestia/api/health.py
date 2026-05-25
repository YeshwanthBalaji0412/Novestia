from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from novestia.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": settings.version,
        "timestamp": datetime.now(UTC).isoformat(),
    }
