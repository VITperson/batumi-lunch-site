"""Menu domain service."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.menu import MenuItem, MenuWeek


class MenuService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_week(self, week_start: date) -> MenuWeek | None:
        stmt = select(MenuWeek).where(MenuWeek.week_start == week_start)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_or_create_week(self, week_start: date, *, title: str | None = None) -> MenuWeek:
        week = await self.get_week(week_start)
        if week is None:
            week = MenuWeek(week_start=week_start, title=title or f"Week of {week_start.isoformat()}")
            self.session.add(week)
            await self.session.flush()
        elif title is not None:
            week.title = title
        return week

    async def list_week_menu(self, week_start: date) -> tuple[MenuWeek | None, dict[str, list[MenuItem]]]:
        week = await self.get_week(week_start)
        if week is None:
            return None, {}
        stmt = (
            select(MenuItem)
            .where(MenuItem.menu_week_id == week.id)
            .order_by(MenuItem.day.asc(), MenuItem.position.asc())
        )
        result = await self.session.execute(stmt)
        items_by_day: dict[str, list[MenuItem]] = {}
        for item in result.scalars():
            items_by_day.setdefault(item.day, []).append(item)
        return week, items_by_day

    async def set_day_items(
        self,
        week: MenuWeek,
        *,
        day: str,
        items: Sequence[dict[str, str | None]],
    ) -> list[MenuItem]:
        normalized_day = day.strip().lower()
        # delete existing items for day
        await self.session.execute(
            delete(MenuItem).where(MenuItem.menu_week_id == week.id, MenuItem.day == normalized_day)
        )
        new_items: list[MenuItem] = []
        for idx, item in enumerate(items):
            menu_item = MenuItem(
                menu_week_id=week.id,
                day=normalized_day,
                position=idx,
                title=str(item.get("title") or item.get("name") or ""),
                description=item.get("description"),
                photo_url=item.get("photo_url"),
            )
            new_items.append(menu_item)
            self.session.add(menu_item)
        await self.session.flush()
        return new_items

    def serialize_week(self, week: MenuWeek, items: dict[str, list[MenuItem]]) -> dict:
        return {
            "weekStart": week.week_start,
            "title": week.title,
            "isPublished": week.is_published,
            "heroImageUrl": week.hero_image_url,
            "items": {
                day: [
                    {
                        "id": str(item.id),
                        "title": item.title,
                        "description": item.description,
                        "photoUrl": item.photo_url,
                        "position": item.position,
                    }
                    for item in day_items
                ]
                for day, day_items in items.items()
            },
        }
