from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session_dep
from app.domain.menu import MenuService
from app.domain.presets import PresetService
from app.domain.order_window import OrderWindowService

from ..schemas.menu import (
    MenuDayPriceResponse,
    MenuDayResponse,
    MenuResponse,
    MenuWeekSummaryResponse,
    PlannerPresetResponse,
)
from ..schemas.order_window import OrderWindowResponse

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/week", response_model=MenuResponse)
async def get_menu_week(
    target_date: date | None = Query(default=None, alias="date"),
    week_start: date | None = Query(default=None, alias="weekStart"),
    session: AsyncSession = Depends(get_session_dep),
) -> MenuResponse:
    service = MenuService(session)
    if week_start:
        week = await service.get_week(week_start=week_start, fallback=False)
    else:
        week = await service.get_week(for_date=target_date or datetime.utcnow().date())
    if not week:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Меню не найдено")
    payload = await service.serialize_week(week)
    return MenuResponse(
        week=payload.week_label,
        weekStart=payload.week_start,
        items=[
            MenuDayResponse(
                day=day.name,
                offerId=day.offer_id,
                status=day.status.value,
                dishes=day.dishes,
                photoUrl=day.photo_url,
                price=MenuDayPriceResponse(amount=day.price_amount, currency=day.price_currency),
                calories=day.calories,
                allergens=day.allergens,
                portionLimit=day.portion_limit,
                portionsReserved=day.portions_reserved,
                portionsAvailable=day.portions_available,
                badge=day.badge,
                orderDeadline=day.order_deadline,
                notes=day.notes,
            )
            for day in payload.days
        ],
    )


@router.get("/weeks", response_model=list[MenuWeekSummaryResponse])
async def list_menu_weeks(session: AsyncSession = Depends(get_session_dep)) -> list[MenuWeekSummaryResponse]:
    service = MenuService(session)
    weeks = await service.list_weeks()
    return [
        MenuWeekSummaryResponse(label=week.week_label, weekStart=week.week_start, isCurrent=week.is_current)
        for week in weeks
    ]


@router.get("/order-window", response_model=OrderWindowResponse)
async def get_order_window(session: AsyncSession = Depends(get_session_dep)) -> OrderWindowResponse:
    service = OrderWindowService(session)
    window = await service.get_window()
    return OrderWindowResponse(enabled=window.next_week_enabled, weekStart=window.week_start)


@router.get("/presets", response_model=list[PlannerPresetResponse])
async def list_presets(session: AsyncSession = Depends(get_session_dep)) -> list[PlannerPresetResponse]:
    service = PresetService(session)
    presets = await service.list_active()
    return [
        PlannerPresetResponse(
            id=preset.id,
            slug=preset.slug,
            title=preset.title,
            description=preset.description,
            days=preset.days,
            portions=preset.portions,
        )
        for preset in presets
    ]
