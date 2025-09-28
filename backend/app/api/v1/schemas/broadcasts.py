from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BroadcastRequest(BaseModel):
    channels: list[str] = Field(default_factory=list)
    html: str


class BroadcastResponse(BaseModel):
    id: str
    status: str
    sentAt: datetime | None


__all__ = ["BroadcastRequest", "BroadcastResponse"]
