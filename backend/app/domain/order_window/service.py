from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.order_window import OrderWindow

DAY_TO_INDEX = {
    "Понедельник": 0,
    "Вторник": 1,
    "Среда": 2,
    "Четверг": 3,
    "Пятница": 4,
}

ORDER_CUTOFF_HOUR = 10


@dataclass(slots=True)
class DayAvailability:
    allowed: bool
    warning: str | None
    is_next_week: bool
    target_week_start: date


class OrderWindowService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_window(self) -> OrderWindow:
        result = await self.session.execute(select(OrderWindow).limit(1))
        window = result.scalar_one_or_none()
        if window is None:
            window = OrderWindow(next_week_enabled=False, week_start=None)
            self.session.add(window)
            await self.session.flush()
        return window

    async def set_window(self, *, enabled: bool, week_start: date | None) -> OrderWindow:
        window = await self.get_window()
        window.next_week_enabled = enabled
        window.week_start = week_start
        await self.session.flush()
        return window

    async def evaluate_day(self, day: str, now: datetime | None = None) -> DayAvailability:
        idx = DAY_TO_INDEX.get(day)
        if idx is None:
            raise ValueError(f"unknown day: {day}")

        now = now or datetime.now()
        today_idx = now.weekday()
        today_date = now.date()

        window = await self.get_window()
        week_start_date: date | None = window.week_start
        next_week_enabled = bool(window.next_week_enabled)

        if week_start_date and next_week_enabled and today_date >= week_start_date:
            # Automatically disable next-week window if start date passed
            window.next_week_enabled = False
            week_start_date = None
            next_week_enabled = False
            await self.session.flush()

        current_week_start = _current_week_start(now)

        if idx < today_idx:
            if next_week_enabled and week_start_date:
                return DayAvailability(True, None, True, week_start_date)
            warning = (
                f"Заказы на {day} уже закрыты для текущей недели. "
                "День снова станет доступен после обновления меню."
            )
            return DayAvailability(False, warning, False, current_week_start)

        if idx == today_idx and now.hour >= ORDER_CUTOFF_HOUR:
            warning = (
                f"Заказы на {day} принимаются до {ORDER_CUTOFF_HOUR:02d}:00 этого дня. "
                "Пожалуйста, выберите другой день."
            )
            return DayAvailability(False, warning, False, current_week_start)

        if next_week_enabled and week_start_date:
            target_week = week_start_date
            is_next_week = today_date < week_start_date
        else:
            target_week = current_week_start
            is_next_week = False

        return DayAvailability(True, None, is_next_week, target_week)


def _current_week_start(now: datetime) -> date:
    return (now - timedelta(days=now.weekday())).date()


__all__ = ["OrderWindowService", "DayAvailability", "ORDER_CUTOFF_HOUR", "DAY_TO_INDEX"]
