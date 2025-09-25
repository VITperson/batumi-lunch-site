"""Utility to migrate legacy JSON data into the PostgreSQL database."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import configure_logging
from app.db import get_session
from app.db.models.menu import MenuItem, MenuWeek
from app.db.models.order import Order
from app.db.models.order_window import OrderWindow
from app.db.models.user import User
from app.domain.menu.service import MenuService
from app.domain.order_window.service import OrderWindowService
from app.domain.users.service import UserService

LOGGER = logging.getLogger("migrate")
DAY_MAPPING = {
    "Понедельник": "monday",
    "Вторник": "tuesday",
    "Среда": "wednesday",
    "Четверг": "thursday",
    "Пятница": "friday",
}


async def ensure_journal(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS data_migration_runs (
                run_id UUID PRIMARY KEY,
                started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                finished_at TIMESTAMPTZ,
                status TEXT NOT NULL DEFAULT 'running',
                notes TEXT
            );
            """
        )
    )


async def journal_update(session: AsyncSession, run_id: uuid.UUID, status: str, notes: str | None = None) -> None:
    await session.execute(
        text(
            "UPDATE data_migration_runs SET finished_at = now(), status = :status, notes = :notes WHERE run_id = :run_id"
        ),
        {"status": status, "notes": notes, "run_id": str(run_id)},
    )


async def journal_start(session: AsyncSession) -> uuid.UUID:
    run_id = uuid.uuid4()
    await session.execute(
        text("INSERT INTO data_migration_runs(run_id) VALUES (:run_id)"), {"run_id": str(run_id)}
    )
    return run_id


def load_json(path: Path) -> Any:
    if not path.exists():
        LOGGER.warning("File %s not found; skipping", path)
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


async def migrate_users(session: AsyncSession, payload: dict[str, Any]) -> None:
    LOGGER.info("Migrating %s users", len(payload))
    service = UserService(session)
    for telegram_id, data in payload.items():
        try:
            tg_id = int(telegram_id)
        except ValueError:
            LOGGER.warning("Invalid telegram id %s; skipping", telegram_id)
            continue
        email = data.get("email")
        user = await service.get_by_telegram(tg_id)
        if user:
            user.full_name = data.get("name") or user.full_name
            user.address = data.get("address") or user.address
            user.phone = data.get("phone") or user.phone
        else:
            user = User(
                telegram_id=tg_id,
                email=email,
                full_name=data.get("name"),
                address=data.get("address"),
                phone=data.get("phone"),
                roles=data.get("roles") or ["customer"],
            )
            session.add(user)
    await session.flush()


def _week_start_from_timestamp(ts: int) -> datetime.date:
    dt = datetime.fromtimestamp(ts)
    return dt.date() - timedelta(days=dt.weekday())


async def migrate_orders(session: AsyncSession, payload: dict[str, Any]) -> None:
    LOGGER.info("Migrating %s orders", len(payload))
    for public_id, data in payload.items():
        status = str(data.get("status") or "new").lower()
        menu_snapshot = data.get("menu") or []
        if isinstance(menu_snapshot, str):
            menu_snapshot = [item.strip() for item in menu_snapshot.split(",") if item.strip()]
        telegram_id = data.get("user_id")
        if telegram_id is None:
            LOGGER.warning("Order %s has no user_id; skipping", public_id)
            continue
        user_stmt = select(User).where(User.telegram_id == int(telegram_id))
        result = await session.execute(user_stmt)
        user = result.scalars().first()
        if user is None:
            user = User(telegram_id=int(telegram_id), roles=["customer"])
            session.add(user)
            await session.flush()
        created_ts = int(data.get("created_at") or 0)
        delivery_week_start = data.get("delivery_week_start")
        if delivery_week_start:
            try:
                week_start = datetime.fromisoformat(delivery_week_start).date()
            except ValueError:
                week_start = _week_start_from_timestamp(created_ts)
        else:
            week_start = _week_start_from_timestamp(created_ts)
        day_ru = data.get("day")
        day = DAY_MAPPING.get(day_ru, str(day_ru).lower())
        stmt = select(Order).where(Order.public_id == public_id)
        existing = (await session.execute(stmt)).scalars().first()
        if existing:
            existing.status = status
            existing.count = int(data.get("count") or existing.count)
            existing.address_snapshot = data.get("address") or existing.address_snapshot
            existing.phone_snapshot = data.get("phone") or existing.phone_snapshot
            existing.menu_snapshot = menu_snapshot or existing.menu_snapshot
            existing.delivery_week_start = week_start
            continue
        order = Order(
            public_id=public_id,
            user_id=user.id,
            day=day,
            count=int(data.get("count") or 1),
            status=status,
            menu_snapshot=menu_snapshot,
            address_snapshot=data.get("address"),
            phone_snapshot=data.get("phone"),
            delivery_week_start=week_start,
            is_next_week=bool(data.get("next_week")),
        )
        session.add(order)
    await session.flush()


async def migrate_menu(session: AsyncSession, payload: dict[str, Any]) -> None:
    LOGGER.info("Migrating menu.json")
    week_label = payload.get("week")
    try:
        week_start = datetime.fromisoformat(str(week_label)).date()
    except ValueError:
        LOGGER.warning("Invalid week label %s; skipping menu", week_label)
        return
    menu_service = MenuService(session)
    week = await menu_service.get_or_create_week(week_start, title=payload.get("title") or f"Menu {week_label}")
    menu_map = payload.get("menu") or {}
    for day_ru, items in menu_map.items():
        normalized_day = DAY_MAPPING.get(day_ru, str(day_ru).lower())
        structured: list[dict[str, str | None]] = []
        if isinstance(items, list):
            structured = [{"title": str(item)} for item in items]
        elif isinstance(items, str):
            structured = [{"title": part.strip()} for part in items.split(",") if part.strip()]
        await menu_service.set_day_items(week, day=normalized_day, items=structured)
    await session.flush()


async def migrate_order_window(session: AsyncSession, payload: dict[str, Any]) -> None:
    LOGGER.info("Migrating order_window.json")
    service = OrderWindowService(session)
    week_start = payload.get("week_start")
    parsed_week = None
    if week_start:
        try:
            parsed_week = datetime.fromisoformat(str(week_start)).date()
        except ValueError:
            LOGGER.warning("Invalid week_start %s; skipping", week_start)
    await service.set_window(enabled=bool(payload.get("next_week_enabled")), week_start=parsed_week, note=None)
    await session.flush()


async def migrate_all() -> None:
    configure_logging()
    async for session in get_session():
        await ensure_journal(session)
        run_id = await journal_start(session)
        try:
            users = load_json(Path("users.json")) or {}
            if isinstance(users, dict):
                await migrate_users(session, users)
            orders = load_json(Path("orders.json")) or {}
            if isinstance(orders, dict):
                await migrate_orders(session, orders)
            menu = load_json(Path("menu.json"))
            if isinstance(menu, dict):
                await migrate_menu(session, menu)
            order_window = load_json(Path("order_window.json")) or {}
            if isinstance(order_window, dict):
                await migrate_order_window(session, order_window)
            await journal_update(session, run_id, "completed")
            await session.commit()
        except Exception as exc:  # pragma: no cover - fault path
            await journal_update(session, run_id, "failed", notes=str(exc))
            await session.rollback()
            LOGGER.exception("Migration failed: %s", exc)
            raise
        finally:
            break


def main() -> None:
    asyncio.run(migrate_all())


if __name__ == "__main__":
    main()
