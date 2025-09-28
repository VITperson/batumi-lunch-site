from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from sqlalchemy import and_, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.enums import DayOfferStatus, DayOfWeek
from app.db.models.menu import DayOffer, MenuItem, MenuWeek


@dataclass(slots=True)
class MenuDay:
    name: str
    dishes: list[str]
    photo_url: str | None
    offer_id: uuid.UUID | None
    status: DayOfferStatus
    price_amount: int
    price_currency: str
    calories: int | None
    allergens: list[str]
    portion_limit: int | None
    portions_reserved: int
    portions_available: int | None
    badge: str | None
    order_deadline: datetime | None
    notes: str | None


@dataclass(slots=True)
class MenuWeekPayload:
    week_label: str
    week_start: date | None
    days: list[MenuDay]


class MenuService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_week(
        self,
        *,
        week_start: date | None = None,
        for_date: date | None = None,
        fallback: bool = True,
    ) -> MenuWeek | None:
        primary_stmt = select(MenuWeek)
        if week_start:
            primary_stmt = primary_stmt.where(MenuWeek.week_start == week_start)
        elif for_date:
            monday = _week_start(for_date)
            primary_stmt = primary_stmt.where(MenuWeek.week_start == monday)
        else:
            primary_stmt = primary_stmt.order_by(MenuWeek.week_start.desc().nullslast(), MenuWeek.created_at.desc())

        result = await self.session.execute(primary_stmt.limit(1))
        week = result.scalar_one_or_none()
        if week or not fallback:
            return week

        fallback_stmt = (
            select(MenuWeek)
            .where(MenuWeek.is_current.is_(True))
            .order_by(MenuWeek.updated_at.desc(), MenuWeek.created_at.desc())
        )
        fallback = (await self.session.execute(fallback_stmt.limit(1))).scalar_one_or_none()
        if fallback:
            return fallback

        latest_stmt = select(MenuWeek).order_by(MenuWeek.week_start.desc().nullslast(), MenuWeek.created_at.desc())
        return (await self.session.execute(latest_stmt.limit(1))).scalar_one_or_none()

    async def get_or_create_current_week(self) -> MenuWeek:
        today = datetime.now().date()
        week = await self.get_week(week_start=_week_start(today))
        if week is None:
            week = MenuWeek(week_label=today.strftime("%d.%m.%Y"), week_start=_week_start(today))
            self.session.add(week)
            await self.session.flush()
        return week

    async def serialize_week(self, week: MenuWeek) -> MenuWeekPayload:
        await self.session.refresh(week)
        week_label = week.week_label
        week_start = week.week_start
        week_day_photos = dict(week.day_photos or {})
        stmt = select(MenuItem).where(MenuItem.week_id == week.id).order_by(MenuItem.day_of_week, MenuItem.position)
        rows = await self.session.execute(stmt)
        items_by_day: dict[str, list[str]] = {day.value: [] for day in DayOfWeek}
        for item in rows.scalars():
            items_by_day.setdefault(item.day_of_week.value, []).append(item.title)

        offers_stmt = select(DayOffer).where(DayOffer.week_id == week.id)
        offers_map: dict[str, DayOffer] = {}
        try:
            offers_result = await self.session.execute(offers_stmt)
        except (ProgrammingError, OperationalError) as error:
            logger.warning("Day offers unavailable, falling back to defaults: %s", error)
            await self.session.rollback()
        else:
            offers_map = {offer.day_of_week.value: offer for offer in offers_result.scalars()}

        ordered_days: Iterable[str] = items_by_day.keys()
        days_payload: list[MenuDay] = []
        for day in ordered_days:
            offer = offers_map.get(day)
            allergens = list(offer.allergens or []) if offer and offer.allergens else []
            days_payload.append(
                MenuDay(
                    name=day,
                    dishes=list(items_by_day.get(day, [])),
                    photo_url=_resolve_photo(day, offer, week_day_photos),
                    offer_id=offer.id if offer else None,
                    status=offer.status if offer else DayOfferStatus.AVAILABLE,
                    price_amount=offer.price_amount if offer else settings.order_price_lari * 100,
                    price_currency=offer.price_currency if offer else "GEL",
                    calories=offer.calories if offer else None,
                    allergens=allergens,
                    portion_limit=offer.portion_limit if offer else None,
                    portions_reserved=offer.portions_reserved if offer else 0,
                    portions_available=_portions_available(offer),
                    badge=offer.badge if offer else None,
                    order_deadline=offer.order_deadline if offer else None,
                    notes=offer.notes if offer else None,
                )
            )

        return MenuWeekPayload(
            week_label=week_label,
            week_start=week_start,
            days=days_payload,
        )

    async def set_week_label(self, week: MenuWeek, title: str) -> MenuWeek:
        week.week_label = title
        await self.session.flush()
        return week

    async def upsert_day_items(self, week: MenuWeek, *, day: DayOfWeek, items: list[str]) -> MenuWeek:
        stmt = select(MenuItem).where(and_(MenuItem.week_id == week.id, MenuItem.day_of_week == day)).order_by(MenuItem.position)
        existing = (await self.session.execute(stmt)).scalars().all()
        normalized = [item.strip() for item in items if item.strip()]

        # Reuse existing rows when possible to retain IDs/order for auditing.
        for idx, item in enumerate(normalized):
            if idx < len(existing):
                existing[idx].title = item
                existing[idx].position = idx
            else:
                self.session.add(MenuItem(week_id=week.id, day_of_week=day, title=item, position=idx))

        for idx in range(len(normalized), len(existing)):
            await self.session.delete(existing[idx])

        await self.session.flush()
        return week

    async def set_day_photo(self, week: MenuWeek, *, day: DayOfWeek, url: str) -> MenuWeek:
        photos = dict(week.day_photos or {})
        photos[day.value] = url
        week.day_photos = photos
        await self.session.flush()
        return week

    async def list_weeks(self, *, limit: int | None = None) -> list[MenuWeek]:
        stmt = select(MenuWeek).order_by(MenuWeek.week_start.desc().nullslast(), MenuWeek.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        rows = await self.session.execute(stmt)
        return list(rows.scalars())


def _week_start(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def _resolve_photo(day: str, offer: DayOffer | None, day_photos: dict[str, str] | None) -> str | None:
    if offer and offer.photo_url:
        return offer.photo_url
    if day_photos:
        return day_photos.get(day)
    return None


def _portions_available(offer: DayOffer | None) -> int | None:
    if not offer or offer.portion_limit is None:
        return None
    available = offer.portion_limit - offer.portions_reserved
    return available if available >= 0 else 0


__all__ = ["MenuService", "MenuDay"]
logger = logging.getLogger(__name__)
