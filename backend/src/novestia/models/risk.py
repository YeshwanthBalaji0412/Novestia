from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novestia.models.base import Base

if TYPE_CHECKING:
    from novestia.models.portfolio import Portfolio


class RiskReport(Base):
    __tablename__ = "risk_reports"
    __table_args__ = (
        Index("ix_risk_reports_portfolio_computed_at", "portfolio_id", "computed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    concentration_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sector_concentration_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volatility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diversification_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cash_ratio_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engine_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    ai_interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    # Relationships
    portfolio: Mapped[Portfolio] = relationship(
        back_populates="risk_reports"
    )
