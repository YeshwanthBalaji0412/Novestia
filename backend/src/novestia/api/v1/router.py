"""Aggregates all v1 API route modules into a single router."""

from fastapi import APIRouter

from novestia.api.v1.ai import router as ai_router
from novestia.api.v1.journal import router as journal_router
from novestia.api.v1.portfolio import router as portfolio_router
from novestia.api.v1.risk import router as risk_router
from novestia.api.v1.stocks import router as stocks_router
from novestia.api.v1.trades import router as trades_router
from novestia.api.v1.users import router as users_router
from novestia.api.v1.watchlist import router as watchlist_router
from novestia.api.v1.ws import router as ws_router

router = APIRouter()
router.include_router(users_router)
router.include_router(stocks_router)
router.include_router(portfolio_router)
router.include_router(watchlist_router)
router.include_router(trades_router)
router.include_router(risk_router)
router.include_router(journal_router)
router.include_router(ai_router)
router.include_router(ws_router)
