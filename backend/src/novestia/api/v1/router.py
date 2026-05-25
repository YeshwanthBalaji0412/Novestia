"""Aggregates all v1 API route modules into a single router."""

from fastapi import APIRouter

from novestia.api.v1.stocks import router as stocks_router
from novestia.api.v1.users import router as users_router
from novestia.api.v1.ws import router as ws_router

router = APIRouter()
router.include_router(users_router)
router.include_router(stocks_router)
router.include_router(ws_router)
