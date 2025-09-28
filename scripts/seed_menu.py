"""Seed database with sample data for local development."""

from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import hash_password
from app.db.models.enums import DayOfferStatus, DayOfWeek, UserRole
from app.db.models.menu import DayOffer, MenuItem, MenuWeek
from app.db.models.preset import PlannerPreset
from app.db.models.order_window import OrderWindow
from app.db.models.user import User
from app.db.session import async_session_factory

SAMPLE_MENU = {
    "Текущая неделя": {
        DayOfWeek.MONDAY: ["Харчо", "Пирожок с мясом", "Салат весенний"],
        DayOfWeek.TUESDAY: ["Окрошка", "Гречка с курицей", "Свекольник"],
        DayOfWeek.WEDNESDAY: ["Чечевичный суп", "Лобио", "Салат с огурцом"],
        DayOfWeek.THURSDAY: ["Тыквенный крем", "Рис с овощами", "Капустный салат"],
        DayOfWeek.FRIDAY: ["Уха", "Картофель по-домашнему", "Бургер вегетарианский"],
    },
    "Следующая неделя": {
        DayOfWeek.MONDAY: ["Минестроне", "Куриный рулет", "Салат Цезарь"],
        DayOfWeek.TUESDAY: ["Суп-пюре из брокколи", "Плов", "Овощной салат"],
        DayOfWeek.WEDNESDAY: ["Солянка", "Картофель по-деревенски", "Винегрет"],
        DayOfWeek.THURSDAY: ["Борщ", "Запечённая рыба", "Салат томаты-моцарелла"],
        DayOfWeek.FRIDAY: ["Сырный суп", "Паста песто", "Греческий салат"],
    },
}

DAY_PHOTOS = {
    DayOfWeek.MONDAY: "/dishphotos/Monday.png",
    DayOfWeek.TUESDAY: "/dishphotos/Tuesday.png",
    DayOfWeek.WEDNESDAY: "/dishphotos/Wednesday.png",
    DayOfWeek.THURSDAY: "/dishphotos/Thursday.png",
    DayOfWeek.FRIDAY: "/dishphotos/Friday.png",
}

DAY_META = {
    DayOfWeek.MONDAY: {"calories": 720, "allergens": ["gluten", "egg"], "badge": "Хит недели"},
    DayOfWeek.TUESDAY: {"calories": 680, "allergens": ["gluten"], "badge": "Легко"},
    DayOfWeek.WEDNESDAY: {"calories": 750, "allergens": ["gluten", "milk"]},
    DayOfWeek.THURSDAY: {"calories": 690, "allergens": ["fish", "gluten"], "badge": "Рыбный день"},
    DayOfWeek.FRIDAY: {"calories": 810, "allergens": ["gluten"], "badge": "Пятница"},
}

DAY_INDEX = {
    DayOfWeek.MONDAY: 0,
    DayOfWeek.TUESDAY: 1,
    DayOfWeek.WEDNESDAY: 2,
    DayOfWeek.THURSDAY: 3,
    DayOfWeek.FRIDAY: 4,
}

SAMPLE_PRESETS = [
    {
        "slug": "full-week",
        "title": "Пн–Пт",
        "description": "Все рабочие дни",
        "days": [day.value for day in DayOfWeek],
        "portions": 1,
        "sort_order": 0,
    },
    {
        "slug": "mon-wed-fri",
        "title": "Пн–Ср–Пт",
        "description": "Оптимальный ритм",
        "days": [DayOfWeek.MONDAY.value, DayOfWeek.WEDNESDAY.value, DayOfWeek.FRIDAY.value],
        "portions": 1,
        "sort_order": 1,
    },
    {
        "slug": "light-start",
        "title": "Пн–Вт",
        "description": "Попробовать на старте недели",
        "days": [DayOfWeek.MONDAY.value, DayOfWeek.TUESDAY.value],
        "portions": 1,
        "sort_order": 2,
    },
]

SAMPLE_USERS = [
    {
        "email": "admin@batumi.lunch",
        "password": "admin123",
        "role": UserRole.ADMIN,
        "address": None
    },
    {
        "email": "customer@batumi.lunch",
        "password": "customer123",
        "role": UserRole.CUSTOMER,
        "address": "ул. Горгиладзе, 5",
    },
]


async def seed_users(session) -> None:
    for payload in SAMPLE_USERS:
        stmt = select(User).where(User.email == payload["email"])
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            continue
        role = payload["role"]
        if isinstance(role, UserRole):
            role_value = role.value
        else:
            role_value = UserRole(role).value

        user = User(
            email=payload["email"],
            password_hash=hash_password(payload["password"]),
            role=role_value,
            address=payload["address"],
            is_active=True,
        )
        session.add(user)


async def seed_menu(session) -> None:
    base_week = date.today() - timedelta(days=date.today().weekday())
    for offset, (label, mapping) in enumerate(SAMPLE_MENU.items()):
        week_start = base_week + timedelta(days=offset * 7)
        stmt = select(MenuWeek).where(MenuWeek.week_label == label)
        week = (await session.execute(stmt)).scalar_one_or_none()
        if not week:
            week = MenuWeek(week_label=label, week_start=week_start)
            session.add(week)
            await session.flush()
        else:
            week.week_start = week_start
        photos = dict(week.day_photos or {})
        for day, dishes in mapping.items():
            stmt_items = select(MenuItem).where(MenuItem.week_id == week.id, MenuItem.day_of_week == day)
            existing = (await session.execute(stmt_items)).scalars().all()
            for idx, dish in enumerate(dishes):
                if idx < len(existing):
                    existing[idx].title = dish
                    existing[idx].position = idx
                else:
                    session.add(MenuItem(week_id=week.id, day_of_week=day, title=dish, position=idx))
            for idx in range(len(dishes), len(existing)):
                await session.delete(existing[idx])

            meta = DAY_META.get(day, {})
            deadline_date = week_start + timedelta(days=DAY_INDEX[day])
            order_deadline = datetime.combine(deadline_date, time(hour=10, minute=0))
            stmt_offer = select(DayOffer).where(DayOffer.week_id == week.id, DayOffer.day_of_week == day)
            offer = (await session.execute(stmt_offer)).scalar_one_or_none()
            price_amount = meta.get("price_amount", 1500)
            price_currency = meta.get("price_currency", "GEL")
            portion_limit = meta.get("portion_limit", 120)
            allergens = list(meta.get("allergens", []))
            if offer:
                offer.status = meta.get("status", DayOfferStatus.AVAILABLE)
                offer.price_amount = price_amount
                offer.price_currency = price_currency
                offer.portion_limit = portion_limit
                offer.portions_reserved = 0
                offer.calories = meta.get("calories")
                offer.allergens = allergens
                offer.badge = meta.get("badge")
                offer.order_deadline = order_deadline
                offer.photo_url = DAY_PHOTOS.get(day)
                offer.notes = meta.get("notes")
            else:
                session.add(
                    DayOffer(
                        week_id=week.id,
                        day_of_week=day,
                        status=meta.get("status", DayOfferStatus.AVAILABLE),
                        price_amount=price_amount,
                        price_currency=price_currency,
                        portion_limit=portion_limit,
                        portions_reserved=0,
                        calories=meta.get("calories"),
                        allergens=allergens,
                        badge=meta.get("badge"),
                        order_deadline=order_deadline,
                        photo_url=DAY_PHOTOS.get(day),
                        notes=meta.get("notes"),
                    )
                )
            photos[day.value] = DAY_PHOTOS.get(day)
        week.day_photos = photos


async def seed_future_weeks(session, *, total_weeks: int = 6) -> None:
    """Ensure placeholder menu weeks exist several weeks ahead."""

    base_week_start = date.today() - timedelta(days=date.today().weekday())
    result = await session.execute(select(MenuWeek.week_start))
    existing_starts = {week_start for week_start in result.scalars() if week_start is not None}

    for index in range(len(SAMPLE_MENU), len(SAMPLE_MENU) + total_weeks):
        week_start = base_week_start + timedelta(days=index * 7)
        if week_start in existing_starts:
            continue
        label = f"Будущая неделя {index - len(SAMPLE_MENU) + 1}"
        session.add(MenuWeek(week_label=label, week_start=week_start))


async def seed_order_window(session) -> None:
    next_week_start = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)
    stmt = select(OrderWindow)
    window = (await session.execute(stmt.limit(1))).scalar_one_or_none()
    if not window:
        window = OrderWindow(next_week_enabled=True, week_start=next_week_start)
        session.add(window)
    else:
        window.next_week_enabled = True
        window.week_start = next_week_start


async def seed_presets(session) -> None:
    for payload in SAMPLE_PRESETS:
        stmt = select(PlannerPreset).where(PlannerPreset.slug == payload["slug"])
        preset = (await session.execute(stmt)).scalar_one_or_none()
        if preset:
            preset.title = payload["title"]
            preset.description = payload["description"]
            preset.days = payload["days"]
            preset.portions = payload["portions"]
            preset.sort_order = payload["sort_order"]
            preset.is_active = True
        else:
            session.add(
                PlannerPreset(
                    slug=payload["slug"],
                    title=payload["title"],
                    description=payload["description"],
                    days=payload["days"],
                    portions=payload["portions"],
                    sort_order=payload["sort_order"],
                    is_active=True,
                )
            )


async def seed() -> None:
    async with async_session_factory() as session:
        await seed_users(session)
        await seed_menu(session)
        await seed_future_weeks(session)
        await seed_order_window(session)
        await seed_presets(session)
        await session.commit()


def main() -> None:
    asyncio.run(seed())
    print("Seed completed.")


if __name__ == "__main__":
    main()
