from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.preset import PlannerPreset


@dataclass(slots=True)
class PresetPayload:
    id: uuid.UUID
    slug: str
    title: str
    description: str | None
    days: list[str]
    portions: int


class PresetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self) -> list[PresetPayload]:
        stmt = (
            select(PlannerPreset)
            .where(PlannerPreset.is_active.is_(True))
            .order_by(PlannerPreset.sort_order.asc(), PlannerPreset.created_at.asc())
        )
        rows = await self.session.execute(stmt)
        return [
            PresetPayload(
                id=preset.id,
                slug=preset.slug,
                title=preset.title,
                description=preset.description,
                days=list(preset.days or []),
                portions=preset.portions,
            )
            for preset in rows.scalars()
        ]


__all__ = ["PresetService", "PresetPayload"]
