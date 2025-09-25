from __future__ import annotations

from datetime import datetime, date
from uuid import UUID

from pydantic import BaseModel, Field, constr


class OrderCreateRequest(BaseModel):
    day: str = Field(..., description="Day of delivery (monday/friday or ru equivalents)")
    count: int = Field(..., ge=1, le=4)
    address: constr(strip_whitespace=True, min_length=5)
    phone: constr(strip_whitespace=True, min_length=5) | None = None
    week_start: date | None = None


class OrderUpdateRequest(BaseModel):
    count: int | None = Field(default=None, ge=1, le=4)
    address: constr(strip_whitespace=True, min_length=5) | None = None

    def model_validate_payload(self) -> None:
        if self.count is None and self.address is None:
            raise ValueError("Either count or address must be provided")


class OrderCancelRequest(BaseModel):
    reason: str | None = None


class OrderResponse(BaseModel):
    id: UUID
    public_id: str
    day: str
    count: int
    status: str
    menu: list[str]
    address: str | None
    phone: str | None
    delivery_week_start: date
    is_next_week: bool
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
