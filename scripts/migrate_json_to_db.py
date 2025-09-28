"""Migrate legacy JSON storage into the relational database.

The script is idempotent: running multiple times keeps data consistent.
It expects the legacy files `users.json`, `orders.json`, `menu.json`, `order_window.json`
from the original Telegram bot to be present next to this script (project root).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.models.enums import DayOfWeek, OrderStatus, UserRole
from app.db.models.menu import MenuItem, MenuWeek
from app.db.models.order import Order
from app.db.models.order_window import OrderWindow
from app.db.models.user import User
from app.db.session import async_session_factory, engine

LEGACY_DIR = Path.cwd()
USERS_FILE = LEGACY_DIR / "users.json"
ORDERS_FILE = LEGACY_DIR / "orders.json"
MENU_FILE = LEGACY_DIR / "menu.json"
ORDER_WINDOW_FILE = LEGACY_DIR / "order_window.json"
LOG_PATH = Path("logs/migrate_json_to_db.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger("migrate-json")


async def migrate_users(session) -> dict[int, User]:
    if not USERS_FILE.exists():
        logger.warning("users.json not found — skipping user migration")
        return {}
    data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    result: dict[int, User] = {}
    for key, payload in data.items():
        try:
            telegram_id = int(key)
        except ValueError:
            logger.warning("Skip user with invalid key: %s", key)
            continue
        stmt = select(User).where(User.telegram_id == telegram_id)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        address = (payload or {}).get("address")
        phone = (payload or {}).get("phone")
        if existing:
            existing.address = address or existing.address
            existing.phone = phone or existing.phone
            result[telegram_id] = existing
            logger.info("Updated user %s", telegram_id)
        else:
            user = User(telegram_id=telegram_id, address=address, phone=phone, role=UserRole.CUSTOMER)
            session.add(user)
            await session.flush()
            result[telegram_id] = user
            logger.info("Inserted user %s", telegram_id)
    return result


def _parse_count(raw: Any) -> int:
    if isinstance(raw, int):
        return raw
    text = str(raw)
    for token in text.split():
        if token.isdigit():
            return int(token)
    raise ValueError(f"cannot parse count from {raw!r}")


def _parse_status(raw: Any) -> OrderStatus:
    try:
        return OrderStatus(str(raw))
    except ValueError:
        return OrderStatus.NEW


def _infer_week_start(day_name: str, created_at: int | None) -> date:
    if created_at:
        dt = datetime.fromtimestamp(created_at)
        monday = dt - timedelta(days=dt.weekday())
        return monday.date()
    # fallback to current week start
    today = datetime.utcnow().date()
    return today - timedelta(days=today.weekday())


async def migrate_orders(session, users_by_telegram: dict[int, User]) -> None:
    if not ORDERS_FILE.exists():
        logger.warning("orders.json not found — skipping order migration")
        return
    data = json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
    for order_id, payload in data.items():
        telegram_id = int(payload.get("user_id", 0))
        user = users_by_telegram.get(telegram_id)
        if not user:
            logger.warning("Skipping order %s: unknown user %s", order_id, telegram_id)
            continue
        count = _parse_count(payload.get("count", 1))
        day_name = str(payload.get("day") or "Понедельник")
        try:
            day = DayOfWeek(day_name)
        except ValueError:
            logger.warning("Unknown day '%s' for order %s", day_name, order_id)
            continue
        created_at = payload.get("created_at")
        delivery_week_start = payload.get("delivery_week_start")
        if delivery_week_start:
            try:
                week_start = date.fromisoformat(str(delivery_week_start))
            except ValueError:
                week_start = _infer_week_start(day_name, created_at)
        else:
            week_start = _infer_week_start(day_name, created_at)
        delivery_date = week_start + timedelta(days={
            DayOfWeek.MONDAY: 0,
            DayOfWeek.TUESDAY: 1,
            DayOfWeek.WEDNESDAY: 2,
            DayOfWeek.THURSDAY: 3,
            DayOfWeek.FRIDAY: 4,
        }[day])

        stmt = select(Order).where(Order.id == order_id)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        menu_items_raw = payload.get("menu")
        if isinstance(menu_items_raw, list):
            menu_items = [str(item).strip() for item in menu_items_raw if str(item).strip()]
        else:
            menu_items = [part.strip() for part in str(menu_items_raw or "").split(",") if part.strip()]
        if not menu_items:
            menu_items = ["Не указано"]

        status = _parse_status(payload.get("status"))
        address = payload.get("address")
        phone = payload.get("phone")

        if existing:
            existing.count = count
            existing.day_of_week = day
            existing.menu_items = menu_items
            existing.status = status
            existing.address = address
            existing.phone = phone
            existing.delivery_week_start = week_start
            existing.delivery_date = delivery_date
            logger.info("Updated order %s", order_id)
        else:
            order = Order(
                id=order_id,
                user_id=user.id,
                day_of_week=day,
                count=count,
                menu_items=menu_items,
                status=status,
                address=address,
                phone=phone,
                delivery_week_start=week_start,
                delivery_date=delivery_date,
                next_week=False,
                unit_price=settings.order_price_lari,
            )
            session.add(order)
            logger.info("Inserted order %s", order_id)


async def migrate_menu(session) -> None:
    if not MENU_FILE.exists():
        logger.warning("menu.json not found — skipping menu migration")
        return
    data = json.loads(MENU_FILE.read_text(encoding="utf-8"))
    week_label = str(data.get("week") or "Legacy menu")
    menu_payload = data.get("menu") or {}
    week_start = None
    if ORDER_WINDOW_FILE.exists():
        try:
            order_window_data = json.loads(ORDER_WINDOW_FILE.read_text(encoding="utf-8"))
            if order_window_data.get("week_start"):
                week_start = date.fromisoformat(order_window_data["week_start"])
        except Exception:
            week_start = None

    stmt = select(MenuWeek).where(MenuWeek.week_label == week_label)
    week = (await session.execute(stmt)).scalar_one_or_none()
    if not week:
        week = MenuWeek(week_label=week_label, week_start=week_start)
        session.add(week)
        await session.flush()
        logger.info("Inserted menu week '%s'", week_label)
    else:
        week.week_start = week_start or week.week_start
        logger.info("Updated menu week '%s'", week_label)

    for day_name, items in menu_payload.items():
        try:
            day = DayOfWeek(day_name)
        except ValueError:
            logger.warning("Skip menu day '%s'", day_name)
            continue
        normalized = []
        if isinstance(items, list):
            normalized = [str(item).strip() for item in items if str(item).strip()]
        else:
            normalized = [part.strip() for part in str(items).split(",") if part.strip()]
        stmt_items = select(MenuItem).where(MenuItem.week_id == week.id, MenuItem.day_of_week == day)
        existing_items = (await session.execute(stmt_items)).scalars().all()
        for idx, title in enumerate(normalized):
            if idx < len(existing_items):
                existing_items[idx].title = title
                existing_items[idx].position = idx
            else:
                session.add(MenuItem(week_id=week.id, day_of_week=day, title=title, position=idx))
        for idx in range(len(normalized), len(existing_items)):
            await session.delete(existing_items[idx])


async def migrate_order_window(session) -> None:
    if not ORDER_WINDOW_FILE.exists():
        logger.warning("order_window.json not found — skipping order window migration")
        return
    data = json.loads(ORDER_WINDOW_FILE.read_text(encoding="utf-8"))
    enabled = bool(data.get("next_week_enabled"))
    week_start_val = data.get("week_start")
    week_start = None
    if week_start_val:
        try:
            week_start = date.fromisoformat(str(week_start_val))
        except ValueError:
            week_start = None
    stmt = select(OrderWindow)
    window = (await session.execute(stmt.limit(1))).scalar_one_or_none()
    if not window:
        window = OrderWindow(next_week_enabled=enabled, week_start=week_start)
        session.add(window)
        logger.info("Inserted order window state")
    else:
        window.next_week_enabled = enabled
        window.week_start = week_start
        logger.info("Updated order window state")


async def migrate() -> None:
    async with async_session_factory() as session:
        users_map = await migrate_users(session)
        await migrate_menu(session)
        await migrate_order_window(session)
        await migrate_orders(session, users_map)
        await session.commit()
        logger.info("Migration finished successfully")


def main() -> None:
    logger.info("Starting migration using database %s", settings.database_url)
    asyncio.run(migrate())


if __name__ == "__main__":
    main()
