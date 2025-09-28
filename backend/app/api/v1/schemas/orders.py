from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrderCreateRequest(BaseModel):
    day: str
    count: int
    address: str
    phone: str | None = None
    weekStart: date | None = None


class OrderUpdateRequest(BaseModel):
    count: int | None = Field(default=None, ge=1)
    address: str | None = None


class OrderCancelRequest(BaseModel):
    reason: str | None = None


class OrderResponse(BaseModel):
    id: str
    day: str
    count: int
    menu: list[str]
    status: str
    address: str | None
    phone: str | None
    deliveryWeekStart: date
    deliveryDate: date
    nextWeek: bool
    createdAt: datetime
    updatedAt: datetime


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]


class PlannerSelectionRequest(BaseModel):
    offerId: UUID
    portions: int = Field(ge=1)


class PlannerWeekSelectionRequest(BaseModel):
    weekStart: date | None = None
    enabled: bool = True
    selections: list[PlannerSelectionRequest] = Field(default_factory=list)


class OrderCalcRequest(BaseModel):
    selections: list[PlannerSelectionRequest] = Field(default_factory=list)
    promoCode: str | None = None
    address: str | None = None
    weeks: list[PlannerWeekSelectionRequest] | None = None


class OrderCalcItemResponse(BaseModel):
    offerId: UUID
    day: str
    status: str
    requestedPortions: int
    acceptedPortions: int
    unitPrice: int
    currency: str
    subtotal: int
    message: str | None = None


class OrderCalcResponse(BaseModel):
    items: list[OrderCalcItemResponse]
    subtotal: int
    discount: int
    total: int
    currency: str
    warnings: list[str] = Field(default_factory=list)
    promoCode: str | None = None
    promoCodeError: str | None = None
    deliveryZone: str | None = None
    deliveryAvailable: bool
    weeks: list["PlannerWeekQuoteResponse"] = Field(default_factory=list)


class PlannerWeekQuoteResponse(BaseModel):
    weekStart: date | None = None
    label: str | None = None
    enabled: bool
    menuStatus: str
    items: list[OrderCalcItemResponse] = Field(default_factory=list)
    subtotal: int
    currency: str | None = None
    warnings: list[str] = Field(default_factory=list)


__all__ = [
    "OrderCreateRequest",
    "OrderUpdateRequest",
    "OrderCancelRequest",
    "OrderResponse",
    "OrderListResponse",
    "PlannerSelectionRequest",
    "PlannerWeekSelectionRequest",
    "OrderCalcRequest",
    "OrderCalcResponse",
    "OrderCalcItemResponse",
    "PlannerWeekQuoteResponse",
]
