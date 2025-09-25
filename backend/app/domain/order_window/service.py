"""Order window service replicating bot logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.order_window import OrderWindow

DAY_TO_INDEX = {
    "monday": 0,
    "понедельник": 0,
    "tuesday": 1,
    "вторник": 1,
    "wednesday": 2,
    "среда": 2,
    "thursday": 3,
    "четверг": 3,
    "friday": 4,
    "пятница": 4,
}


@dataclass(slots=True)
class OrderWindowDecision:
    allowed: bool
    reason: str | None
    is_next_week: bool
    week_start: date


class OrderWindowService:
    """Service handling order window availability toggles."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._tz = ZoneInfo(settings.timezone)

    async def get_window(self) -> OrderWindow | None:
        stmt = select(OrderWindow).order_by(OrderWindow.created_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def set_window(self, *, enabled: bool, week_start: date | None, note: str | None = None) -> OrderWindow:
        window = await self.get_window()
        if window is None:
            window = OrderWindow(is_enabled=enabled, week_start=week_start, note=note)
            self.session.add(window)
        else:
            window.is_enabled = enabled
            window.week_start = week_start
            window.note = note
        await self.session.flush()
        return window

    async def determine(self, day: str, *, now: datetime | None = None) -> OrderWindowDecision:
        normalized = day.strip().lower()
        if normalized not in DAY_TO_INDEX:
            return OrderWindowDecision(False, "Неверный день недели.", False, self._monday(self._now(now).date()))
        idx = DAY_TO_INDEX[normalized]
        now_local = self._now(now)
        today_idx = now_local.weekday()
        current_week_start = self._monday(now_local.date())

        window = await self.get_window()
        next_week_enabled = bool(window and window.is_enabled)
        week_start = window.week_start if window else None
        if next_week_enabled and week_start:
            if week_start <= now_local.date():
                # window expired -> disable automatically
                window.is_enabled = False
                window.week_start = None
                next_week_enabled = False
                week_start = None
                await self.session.flush()
        is_next_week = False
        target_week = current_week_start
        reason: str | None = None

        if idx < today_idx:
            if next_week_enabled and week_start:
                is_next_week = True
                target_week = week_start
            else:
                reason = (
                    "Заказы на выбранный день закрыты для текущей недели."
                    " Дождитесь обновления меню или откройте приём на следующую неделю."
                )
                return OrderWindowDecision(False, reason, False, current_week_start)
        elif idx == today_idx and now_local.hour >= settings.order_cutoff_hour:
            cutoff_str = f"{settings.order_cutoff_hour:02d}:00"
            reason = f"Заказы на выбранный день принимаются до {cutoff_str}."
            return OrderWindowDecision(False, reason, False, current_week_start)

        if next_week_enabled and week_start and idx < today_idx:
            target_week = week_start
            is_next_week = True

        return OrderWindowDecision(True, None, is_next_week, target_week)

    def _now(self, now: datetime | None) -> datetime:
        if now is None:
            return datetime.now(tz=self._tz)
        if now.tzinfo is None:
            return now.replace(tzinfo=self._tz)
        return now.astimezone(self._tz)

    def _monday(self, any_date: date) -> date:
        return any_date - timedelta(days=any_date.weekday())
