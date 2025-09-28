from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class OrderWindowRequest(BaseModel):
    enabled: bool
    weekStart: date | None = None


class OrderWindowResponse(BaseModel):
    enabled: bool
    weekStart: date | None


__all__ = ["OrderWindowRequest", "OrderWindowResponse"]
