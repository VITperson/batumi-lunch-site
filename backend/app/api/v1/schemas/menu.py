from __future__ import annotations

from datetime import date
from pydantic import BaseModel, Field, HttpUrl


class MenuWeekRequest(BaseModel):
    week_start: date
    title: str = Field(..., min_length=3)
    publish: bool | None = None


class MenuItemPayload(BaseModel):
    title: str = Field(..., min_length=2)
    description: str | None = None
    photo_url: HttpUrl | str | None = None


class MenuDayUpdateRequest(BaseModel):
    week_start: date
    day: str
    items: list[MenuItemPayload]


class MenuWeekResponse(BaseModel):
    week_start: date
    title: str
    is_published: bool
    hero_image_url: str | None
    items: dict[str, list[MenuItemPayload]]
