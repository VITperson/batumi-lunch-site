from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BroadcastRequest(BaseModel):
    channels: list[str] = Field(default_factory=lambda: ["email"])
    subject: str | None = None
    html: str = Field(..., min_length=1)


class BroadcastResponse(BaseModel):
    id: UUID
    status: str
    sent: int
    failed: int
    created_at: datetime
