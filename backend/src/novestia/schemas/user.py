from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    onboarded: bool
    portfolio_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OnboardRequest(BaseModel):
    display_name: str | None = None


class OnboardResponse(BaseModel):
    user: UserResponse
    portfolio_id: uuid.UUID
