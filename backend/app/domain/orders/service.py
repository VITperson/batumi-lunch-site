"""Order domain service implementing business rules from the bot."""

from __future__ import annotations

import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.order import Order
from app.db.models.user import User
from app.domain.menu.service import MenuService
from app.domain.order_window.service import OrderWindowService
from .errors import DuplicateOrderError, OrderNotFoundError, OrderValidationError, OrderWindowClosedError

ACTIVE_STATUSES = {"new", "confirmed"}
ALLOWED_COUNTS = {1, 2, 3, 4}
DAY_MAPPING = {
    "понедельник": "monday",
    "monday": "monday",
    "вторник": "tuesday",
    "tuesday": "tuesday",
    "среда": "wednesday",
    "wednesday": "wednesday",
    "четверг": "thursday",
    "thursday": "thursday",
    "пятница": "friday",
    "friday": "friday",
}


@dataclass(slots=True)
class OrderCreateData:
    day: str
    count: int
    address: str
    phone: str | None
    week_start: date | None = None


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.menu_service = MenuService(session)
        self.window_service = OrderWindowService(session)

    async def create(self, user: User, data: OrderCreateData) -> Order:
        normalized_day = self._normalize_day(data.day)
        if data.count not in ALLOWED_COUNTS:
            raise OrderValidationError("count", "Количество обедов должно быть от 1 до 4.")
        if not data.address.strip():
            raise OrderValidationError("address", "Адрес доставки обязателен.")

        decision = await self.window_service.determine(normalized_day)
        if not decision.allowed:
            raise OrderWindowClosedError(day=normalized_day, message=decision.reason or "Приём заказов закрыт.")

        delivery_week = decision.week_start

        existing = await self._find_active_duplicate(user.id, normalized_day, delivery_week)
        if existing:
            raise DuplicateOrderError(
                existing_order_id=existing.public_id,
                day=normalized_day,
                week_start=delivery_week.isoformat(),
            )

        menu_week, items_by_day = await self.menu_service.list_week_menu(delivery_week)
        if not menu_week:
            raise OrderValidationError("menu", "Меню для выбранной недели не опубликовано.")
        menu_items = items_by_day.get(normalized_day, [])
        if not menu_items:
            raise OrderValidationError("menu", "Меню для выбранного дня отсутствует.")

        public_id = self._generate_public_id(user.telegram_id or user.email or str(user.id))
        order = Order(
            public_id=public_id,
            user_id=user.id,
            menu_week_id=menu_week.id,
            day=normalized_day,
            count=data.count,
            status="new",
            menu_snapshot=[item.title for item in menu_items],
            address_snapshot=data.address,
            phone_snapshot=data.phone,
            delivery_week_start=delivery_week,
            is_next_week=decision.is_next_week,
        )
        self.session.add(order)
        # update user profile snapshot for address/phone if missing or changed
        changed = False
        if (user.address or "").strip() != data.address.strip():
            user.address = data.address.strip()
            changed = True
        if data.phone and (user.phone or "").strip() != data.phone.strip():
            user.phone = data.phone.strip()
            changed = True
        if changed:
            await self.session.flush()
        await self.session.flush()
        return order

    async def _find_active_duplicate(self, user_id: uuid.UUID, day: str, week_start: date) -> Order | None:
        stmt = (
            select(Order)
            .where(
                and_(
                    Order.user_id == user_id,
                    Order.day == day,
                    Order.delivery_week_start == week_start,
                    Order.status.in_(list(ACTIVE_STATUSES)),
                )
            )
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update(self, user: User, public_id: str, *, count: int | None = None, address: str | None = None) -> Order:
        order = await self.get_by_public_id(public_id)
        if order.user_id != user.id and "admin" not in (user.roles or []):
            raise OrderValidationError("permissions", "Редактирование разрешено только владельцу или администратору.")
        if order.status not in ACTIVE_STATUSES:
            raise OrderValidationError("status", "Заказ уже обработан и не может быть изменён.")
        if count is not None:
            if count not in ALLOWED_COUNTS:
                raise OrderValidationError("count", "Количество обедов должно быть от 1 до 4.")
            order.count = count
        if address:
            order.address_snapshot = address.strip()
            if order.user_id == user.id:
                user.address = order.address_snapshot
        if count is None and address is None:
            raise OrderValidationError("payload", "Не переданы данные для обновления.")
        await self.session.flush()
        return order

    async def cancel(self, user: User, public_id: str, *, admin_override: bool = False) -> Order:
        order = await self.get_by_public_id(public_id)
        is_owner = order.user_id == user.id
        is_admin = "admin" in (user.roles or []) or admin_override
        if not (is_owner or is_admin):
            raise OrderValidationError("permissions", "Отменять заказ может только владелец или администратор.")
        if order.status not in ACTIVE_STATUSES:
            raise OrderValidationError("status", "Невозможно отменить заказ с текущим статусом.")
        order.status = "cancelled_by_user" if is_owner and not is_admin else "cancelled"
        order.cancelled_at = datetime.now(timezone.utc)
        await self.session.flush()
        return order

    async def get_by_public_id(self, public_id: str) -> Order:
        stmt = select(Order).where(Order.public_id == public_id)
        result = await self.session.execute(stmt)
        order = result.scalars().first()
        if not order:
            raise OrderNotFoundError(public_id)
        return order

    async def list_for_user(self, user: User) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.user_id == user.id)
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def list_for_week(self, week_start: date, statuses: Iterable[str] | None = None) -> list[Order]:
        stmt = select(Order).where(Order.delivery_week_start == week_start)
        if statuses:
            stmt = stmt.where(Order.status.in_(list(statuses)))
        stmt = stmt.order_by(Order.day.asc(), Order.created_at.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def set_status(self, public_id: str, status: str) -> None:
        await self.session.execute(
            update(Order)
            .where(Order.public_id == public_id)
            .values(status=status, updated_at=datetime.now(timezone.utc))
        )

    def _normalize_day(self, day: str) -> str:
        normalized = DAY_MAPPING.get(day.strip().lower())
        if not normalized:
            raise OrderValidationError("day", "Допустимы только будние дни (понедельник-пятница).")
        return normalized

    def _generate_public_id(self, seed: str | int | None) -> str:
        base = int(time.time())
        uid_part = str(seed or "0")
        return f"BLB-{self._base36(base)}-{self._base36_hash(uid_part)}-{self._base36_random()}"

    def _base36(self, value: int) -> str:
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if value == 0:
            return "0"
        sign = "-" if value < 0 else ""
        value = abs(value)
        digits = []
        while value:
            value, rem = divmod(value, 36)
            digits.append(chars[rem])
        return sign + "".join(reversed(digits))

    def _base36_hash(self, value: str) -> str:
        hashed = abs(hash(value)) % (36**4)
        return self._base36(hashed).rjust(4, "0")[-4:]

    def _base36_random(self) -> str:
        return self._base36(secrets.randbits(20)).rjust(4, "0")[:4]
