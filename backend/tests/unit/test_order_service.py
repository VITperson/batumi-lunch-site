from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta

import pytest

from app.domain.orders.errors import DuplicateOrderError, OrderValidationError, OrderWindowClosedError
from app.domain.orders.service import OrderCreateData, OrderService
from app.domain.order_window.service import OrderWindowService
from app.db.models.menu import MenuItem, MenuWeek
from app.db.models.order import Order
from app.db.models.order_window import OrderWindow
from app.db.models.user import User
from app.db.models.enums import UserRole


@pytest.fixture()
async def user(async_session):
    user = User(email="user@example.com", roles=[UserRole.customer.value])
    async_session.add(user)
    await async_session.flush()
    return user


def _next_monday() -> date:
    today = datetime.utcnow().date()
    return today + timedelta(days=(7 - today.weekday()) % 7)


async def _prepare_menu(async_session, week_start: date, day: str) -> None:
    week = MenuWeek(week_start=week_start, title="Test Week", is_published=True)
    async_session.add(week)
    await async_session.flush()
    item = MenuItem(menu_week_id=week.id, day=day, position=0, title="Комплексный обед")
    async_session.add(item)
    await async_session.flush()


async def _prepare_order_window(async_session, week_start: date) -> None:
    async_session.add(OrderWindow(is_enabled=True, week_start=week_start))
    await async_session.flush()


@pytest.mark.asyncio
async def test_create_order_success(async_session, user):
    week_start = _next_monday()
    await _prepare_menu(async_session, week_start, "monday")
    await _prepare_order_window(async_session, week_start)
    service = OrderService(async_session)

    order = await service.create(
        user,
        OrderCreateData(day="monday", count=2, address="Main st 1", phone="+995512345678"),
    )
    await async_session.commit()

    assert order.count == 2
    assert order.menu_snapshot == ["Комплексный обед"]
    assert order.delivery_week_start == week_start
    assert order.status == "new"


@pytest.mark.asyncio
async def test_duplicate_order_prevented(async_session, user):
    week_start = _next_monday()
    await _prepare_menu(async_session, week_start, "monday")
    await _prepare_order_window(async_session, week_start)
    service = OrderService(async_session)

    await service.create(user, OrderCreateData(day="monday", count=1, address="Addr", phone=None))
    await async_session.flush()

    with pytest.raises(DuplicateOrderError):
        await service.create(user, OrderCreateData(day="monday", count=1, address="Addr", phone=None))


@pytest.mark.asyncio
async def test_order_window_closed(async_session, user, monkeypatch):
    week_start = _next_monday()
    await _prepare_menu(async_session, week_start, "monday")
    service = OrderService(async_session)

    original_determine = service.window_service.determine

    async def forced_determine(day: str, now=None):
        future_now = datetime.utcnow() + timedelta(days=3)
        return await original_determine(day, now=future_now)

    monkeypatch.setattr(service.window_service, "determine", forced_determine)

    with pytest.raises(OrderWindowClosedError):
        await service.create(user, OrderCreateData(day="monday", count=1, address="Addr", phone=None))


@pytest.mark.asyncio
async def test_order_count_validation(async_session, user):
    week_start = _next_monday()
    await _prepare_menu(async_session, week_start, "monday")
    await _prepare_order_window(async_session, week_start)
    service = OrderService(async_session)

    with pytest.raises(OrderValidationError):
        await service.create(user, OrderCreateData(day="monday", count=10, address="Addr", phone=None))


@pytest.mark.asyncio
async def test_admin_cancel(async_session):
    admin = User(email="admin@example.com", roles=[UserRole.admin.value])
    async_session.add(admin)
    await async_session.flush()
    week_start = _next_monday()
    await _prepare_menu(async_session, week_start, "monday")
    await _prepare_order_window(async_session, week_start)
    service = OrderService(async_session)
    order = await service.create(admin, OrderCreateData(day="monday", count=1, address="Addr", phone=None))
    await async_session.flush()

    cancelled = await service.cancel(admin, order.public_id)
    await async_session.flush()

    assert cancelled.status == "cancelled"
