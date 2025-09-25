"""Seed script for Batumi Lunch demo data."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging
from app.db import get_session
from app.db.models.user import User
from app.domain.menu.service import MenuService
from app.domain.order_window.service import OrderWindowService
from app.domain.orders.errors import DuplicateOrderError
from app.domain.orders.service import OrderCreateData, OrderService
from app.domain.users.service import UserService

LOGGER = logging.getLogger("seed")

MENU_TEMPLATE = {
    "monday": ["Салат с нутом", "Томатный суп", "Лимонад"],
    "tuesday": ["Хачапури", "Салат коул-слоу", "Компот"],
    "wednesday": ["Лобио", "Лаваш", "Морс"],
    "thursday": ["Цыплёнок табака", "Картофель по-деревенски", "Айран"],
    "friday": ["Форель на гриле", "Овощи", "Смузи"]
}


def current_week_start(base: date | None = None) -> date:
    base = base or datetime.utcnow().date()
    return base - timedelta(days=base.weekday())


async def seed() -> None:
    configure_logging()
    async for session in get_session():
        user_service = UserService(session)
        admin_email = settings.default_admin_email or "admin@batumi.lunch"
        admin = await user_service.ensure_admin(email=admin_email, password="changeme")
        LOGGER.info("Admin user ready: %s", admin.email)

        customer = await user_service.get_by_email("demo@batumi.lunch")
        if customer is None:
            customer = await user_service.create_user(
                email="demo@batumi.lunch",
                password="demo",
                telegram_id=None,
                full_name="Demo Customer",
                roles=["customer"],
            )
            customer.address = "ул. Руставели 10"
            customer.phone = "+995500000001"
        await session.flush()

        menu_service = MenuService(session)
        order_service = OrderService(session)
        window_service = OrderWindowService(session)

        week_start = current_week_start()
        next_week = week_start + timedelta(days=7)

        for target_week, title in ((week_start, "Текущая неделя"), (next_week, "Следующая неделя")):
            week = await menu_service.get_or_create_week(target_week, title=title)
            for day, items in MENU_TEMPLATE.items():
                structured = [{"title": dish} for dish in items]
                await menu_service.set_day_items(week, day=day, items=structured)
        await session.flush()

        await window_service.set_window(enabled=True, week_start=next_week, note="Seeded data")

        try:
            await order_service.create(
                customer,
                OrderCreateData(day="monday", count=2, address=customer.address or "", phone=customer.phone),
            )
        except DuplicateOrderError:
            pass

        await session.commit()
        break


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
