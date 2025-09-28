from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MenuDayPriceResponse(BaseModel):
    amount: int
    currency: str


class MenuDayResponse(BaseModel):
    day: str
    offerId: UUID | None = None
    status: str
    dishes: list[str] = Field(default_factory=list)
    photoUrl: str | None = None
    price: MenuDayPriceResponse
    calories: int | None = None
    allergens: list[str] = Field(default_factory=list)
    portionLimit: int | None = None
    portionsReserved: int = 0
    portionsAvailable: int | None = None
    badge: str | None = None
    orderDeadline: datetime | None = None
    notes: str | None = None


class MenuResponse(BaseModel):
    week: str
    weekStart: date | None
    items: list[MenuDayResponse]


class MenuUpdateRequest(BaseModel):
    items: list[str] = Field(default_factory=list)


class MenuWeekRequest(BaseModel):
    title: str


class MenuWeekSummaryResponse(BaseModel):
    label: str
    weekStart: date | None
    isCurrent: bool


class PlannerPresetResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    description: str | None = None
    days: list[str] = Field(default_factory=list)
    portions: int = 1


__all__ = [
    "MenuResponse",
    "MenuDayResponse",
    "MenuUpdateRequest",
    "MenuWeekRequest",
    "MenuWeekSummaryResponse",
    "PlannerPresetResponse",
]
