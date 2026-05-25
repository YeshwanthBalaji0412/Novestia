from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novestia.models.base import Base


class Stock(Base):
    __tablename__ = "stocks"
    __table_args__ = (
        CheckConstraint(
            "instrument_type IN ('STOCK', 'ETF')",
            name="ck_stocks_instrument_type",
        ),
    )

    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    exchange: Mapped[str | None] = mapped_column(String, nullable=True)
    sector: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    instrument_type: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    metadata_updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Relationships
    snapshot: Mapped[StockSnapshot | None] = relationship(back_populates="stock")
    price_history: Mapped[list[PriceHistory]] = relationship(back_populates="stock")


class StockSnapshot(Base):
    __tablename__ = "stock_snapshots"

    ticker: Mapped[str] = mapped_column(
        String, ForeignKey("stocks.ticker"), primary_key=True
    )
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    previous_close: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    market_cap: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    eps: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    week_52_high: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    week_52_low: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    beta: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    expense_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    snapshot_taken_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Relationships
    stock: Mapped[Stock] = relationship(back_populates="snapshot")


class PriceHistory(Base):
    """TimescaleDB hypertable — partitioned by recorded_at.

    Note: The hypertable conversion is handled in a separate Alembic migration
    (002_enable_timescaledb) since it requires the TimescaleDB extension.
    This model defines the table structure only.
    """

    __tablename__ = "price_history"
    __table_args__ = (
        Index("ix_price_history_ticker_recorded_at", "ticker", "recorded_at"),
    )

    # No UUID PK — TimescaleDB hypertables work best with time-based PKs.
    # Using composite (ticker, recorded_at) as the effective unique identifier.
    ticker: Mapped[str] = mapped_column(
        String, ForeignKey("stocks.ticker"), primary_key=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), primary_key=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    stock: Mapped[Stock] = relationship(back_populates="price_history")
