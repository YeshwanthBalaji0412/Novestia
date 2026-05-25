"""All SQLAlchemy models — imported here so Alembic can discover them."""

from novestia.models.ai import AIExplanation
from novestia.models.base import Base
from novestia.models.portfolio import (
    Holding,
    JournalEntry,
    Portfolio,
    PortfolioSnapshot,
    Transaction,
)
from novestia.models.risk import RiskReport
from novestia.models.stock import PriceHistory, Stock, StockSnapshot
from novestia.models.system import APICallLog
from novestia.models.user import User
from novestia.models.watchlist import Watchlist, WatchlistItem

__all__ = [
    "AIExplanation",
    "APICallLog",
    "Base",
    "Holding",
    "JournalEntry",
    "Portfolio",
    "PortfolioSnapshot",
    "PriceHistory",
    "RiskReport",
    "Stock",
    "StockSnapshot",
    "Transaction",
    "User",
    "Watchlist",
    "WatchlistItem",
]
