from __future__ import annotations

from datetime import timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.db.models.enums import DayOfferStatus, DayOfWeek, OrderStatus, UserRole
from app.db.models.menu import DayOffer, MenuItem, MenuWeek
from app.db.models.order_window import OrderWindow
from app.db.models.user import User
from app.domain.menu import MenuService
from app.domain.order_window import OrderWindowService
from app.domain.orders import (
    DuplicateOrderError,
    OrderDraft,
    OrderService,
    PlannerSelection,
    PlannerWeekRequest,
)


@pytest_asyncio.fixture()
async def user(session):
    instance = User(email="test@example.com", role=UserRole.CUSTOMER)
    session.add(instance)
    await session.flush()
    return instance


@pytest_asyncio.fixture()
async def menu_week(session, now):
    week_start = now.date() + timedelta(days=(7 - now.date().weekday()) % 7)
    week = MenuWeek(week_label="Test Week", week_start=week_start)
    session.add(week)
    await session.flush()
    item = MenuItem(week_id=week.id, day_of_week=DayOfWeek.FRIDAY, title="Суп дня", position=0)
    session.add(item)
    offer = DayOffer(
        week_id=week.id,
        day_of_week=DayOfWeek.FRIDAY,
        status=DayOfferStatus.AVAILABLE,
        price_amount=1500,
        price_currency="GEL",
        portion_limit=50,
        portions_reserved=0,
    )
    session.add(offer)
    await session.flush()
    return week


@pytest_asyncio.fixture()
async def order_window(session, menu_week):
    window = OrderWindow(next_week_enabled=True, week_start=menu_week.week_start)
    session.add(window)
    await session.flush()
    return window


@pytest.mark.asyncio
async def test_create_order_success(session, user, menu_week, order_window):
    menu_service = MenuService(session)
    window_service = OrderWindowService(session)
    service = OrderService(session, menu_service=menu_service, window_service=window_service)

    draft = OrderDraft(day=DayOfWeek.FRIDAY, count=2, address="ул. Руставели, 10", phone="+995123456")
    order = await service.create_order(user=user, draft=draft)

    assert order.count == 2
    assert order.status == OrderStatus.NEW
    assert order.menu_items == ["Суп дня"]
    assert order.id.startswith("BLB-")


@pytest.mark.asyncio
async def test_create_order_duplicate(session, user, menu_week, order_window):
    menu_service = MenuService(session)
    window_service = OrderWindowService(session)
    service = OrderService(session, menu_service=menu_service, window_service=window_service)

    draft = OrderDraft(day=DayOfWeek.FRIDAY, count=1, address="Адрес", phone=None)
    await service.create_order(user=user, draft=draft)

    with pytest.raises(DuplicateOrderError):
        await service.create_order(user=user, draft=draft)


@pytest.mark.asyncio
async def test_calculate_planner_quote_multi_week(session, menu_week, order_window):
    menu_service = MenuService(session)
    window_service = OrderWindowService(session)
    service = OrderService(session, menu_service=menu_service, window_service=window_service)

    first_offer = (
        await session.execute(select(DayOffer).where(DayOffer.week_id == menu_week.id))
    ).scalar_one()

    assert menu_week.week_start is not None
    second_week_start = menu_week.week_start + timedelta(days=7)
    second_week = MenuWeek(week_label="Second Week", week_start=second_week_start)
    session.add(second_week)
    await session.flush()

    second_item = MenuItem(week_id=second_week.id, day_of_week=DayOfWeek.MONDAY, title="Салат", position=0)
    session.add(second_item)
    second_offer = DayOffer(
        week_id=second_week.id,
        day_of_week=DayOfWeek.MONDAY,
        status=DayOfferStatus.AVAILABLE,
        price_amount=1700,
        price_currency="GEL",
        portion_limit=30,
        portions_reserved=0,
    )
    session.add(second_offer)
    await session.flush()

    weeks = [
        PlannerWeekRequest(
            week_start=menu_week.week_start,
            enabled=True,
            selections=[PlannerSelection(offer_id=first_offer.id, portions=2)],
        ),
        PlannerWeekRequest(
            week_start=second_week_start,
            enabled=True,
            selections=[PlannerSelection(offer_id=second_offer.id, portions=3)],
        ),
        PlannerWeekRequest(
            week_start=second_week_start + timedelta(days=7),
            enabled=True,
            selections=[],
        ),
    ]

    quote = await service.calculate_planner_quote(selections=[], weeks=weeks)

    expected_subtotal = 2 * first_offer.price_amount + 3 * second_offer.price_amount
    assert quote.subtotal == expected_subtotal
    assert quote.total == expected_subtotal
    assert quote.discount == 0
    assert quote.currency == "GEL"
    assert len(quote.weeks) == 3
    assert quote.weeks[0].subtotal == 2 * first_offer.price_amount
    assert quote.weeks[0].menu_status == "published"
    assert quote.weeks[1].subtotal == 3 * second_offer.price_amount
    assert quote.weeks[1].menu_status == "published"
    assert quote.weeks[2].subtotal == 0
    assert quote.weeks[2].menu_status in {"pending", "empty"}
    assert quote.items
    assert quote.items[0].offer_id == first_offer.id


@pytest.mark.asyncio
async def test_calculate_planner_quote_pending_week_freezes_price(session, menu_week, order_window):
    menu_service = MenuService(session)
    window_service = OrderWindowService(session)
    service = OrderService(session, menu_service=menu_service, window_service=window_service)

    first_offer = (
        await session.execute(select(DayOffer).where(DayOffer.week_id == menu_week.id))
    ).scalar_one()

    assert menu_week.week_start is not None
    future_week_start = menu_week.week_start + timedelta(days=7)

    weeks = [
        PlannerWeekRequest(
            week_start=menu_week.week_start,
            enabled=True,
            selections=[PlannerSelection(offer_id=first_offer.id, portions=1)],
        ),
        PlannerWeekRequest(
            week_start=future_week_start,
            enabled=True,
            selections=[PlannerSelection(offer_id=first_offer.id, portions=2)],
        ),
    ]

    quote = await service.calculate_planner_quote(selections=[], weeks=weeks)

    assert len(quote.weeks) == 2
    assert quote.weeks[1].menu_status == "pending"
    assert quote.weeks[1].subtotal == 2 * first_offer.price_amount
    assert quote.weeks[1].items
    reserved_line = quote.weeks[1].items[0]
    assert reserved_line.status == "reserved"
    assert reserved_line.subtotal == 2 * first_offer.price_amount
    assert reserved_line.message and "Меню уточняется" in reserved_line.message
