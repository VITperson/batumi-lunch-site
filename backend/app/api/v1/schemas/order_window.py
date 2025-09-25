from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class OrderWindowRequest(BaseModel):
    enabled: bool
    week_start: date | None = None
    note: str | None = None


class OrderWindowResponse(BaseModel):
    is_enabled: bool
    week_start: date | None
    note: str | None
    updated_at: datetime
