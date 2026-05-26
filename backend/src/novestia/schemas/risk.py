from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class SubscoreResponse(BaseModel):
    score: int
    explanation: str


class RiskReportResponse(BaseModel):
    id: uuid.UUID
    overall_score: int
    subscores: dict[str, SubscoreResponse]
    engine_explanation: str
    ai_interpretation: str | None
    computed_at: datetime

    model_config = {"from_attributes": True}


class RiskHistoryPoint(BaseModel):
    overall_score: int
    computed_at: datetime
