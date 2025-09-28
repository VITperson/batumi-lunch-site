from __future__ import annotations

import io
from datetime import datetime, timedelta

import boto3
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_redis, get_session_dep
from app.core.config import settings
from app.db.models.enums import DayOfWeek
from app.domain.broadcasts import BroadcastService
from app.domain.menu import MenuDay, MenuService
from app.domain.order_window import OrderWindowService

from ..schemas.broadcasts import BroadcastRequest, BroadcastResponse
from ..schemas.menu import MenuDayPriceResponse, MenuDayResponse, MenuResponse, MenuUpdateRequest, MenuWeekRequest
from ..schemas.order_window import OrderWindowRequest, OrderWindowResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def _build_menu_service(session: AsyncSession) -> MenuService:
    return MenuService(session)


def _build_order_window_service(session: AsyncSession) -> OrderWindowService:
    return OrderWindowService(session)


async def _rate_limit_broadcasts(redis: Redis | None, admin_id: str) -> None:
    if not redis:
        return
    key = f"{settings.broadcasts_rate_limit_key_prefix}:{admin_id}"
    ttl = await redis.ttl(key)
    if ttl and ttl > 0:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Broadcast rate limit exceeded")
    await redis.set(key, "1", ex=60)


def _serialize_menu_day(payload: MenuDay) -> MenuDayResponse:
    return MenuDayResponse(
        day=payload.name,
        offerId=payload.offer_id,
        status=payload.status.value,
        dishes=payload.dishes,
        photoUrl=payload.photo_url,
        price=MenuDayPriceResponse(amount=payload.price_amount, currency=payload.price_currency),
        calories=payload.calories,
        allergens=payload.allergens,
        portionLimit=payload.portion_limit,
        portionsReserved=payload.portions_reserved,
        portionsAvailable=payload.portions_available,
        badge=payload.badge,
        orderDeadline=payload.order_deadline,
        notes=payload.notes,
    )


@router.put("/menu/week", response_model=MenuResponse)
async def set_menu_week_title(
    request: MenuWeekRequest,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_session_dep),
) -> MenuResponse:
    service = _build_menu_service(session)
    week = await service.get_or_create_current_week()
    await service.set_week_label(week, request.title)
    payload = await service.serialize_week(week)
    return MenuResponse(
        week=payload.week_label,
        weekStart=payload.week_start,
        items=[_serialize_menu_day(day) for day in payload.days],
    )


@router.put("/menu/{day}", response_model=MenuResponse)
async def set_menu_day(
    day: str,
    request: MenuUpdateRequest,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_session_dep),
) -> MenuResponse:
    try:
        enum_day = DayOfWeek(day)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный день недели") from exc
    service = _build_menu_service(session)
    week = await service.get_or_create_current_week()
    await service.upsert_day_items(week, day=enum_day, items=request.items)
    payload = await service.serialize_week(week)
    return MenuResponse(
        week=payload.week_label,
        weekStart=payload.week_start,
        items=[_serialize_menu_day(item) for item in payload.days],
    )


@router.post("/menu/photo", response_model=MenuDayResponse)
async def upload_menu_photo(
    day: str = Form(...),
    file: UploadFile = File(...),
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_session_dep),
) -> MenuDayResponse:
    try:
        enum_day = DayOfWeek(day)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный день недели") from exc

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой файл")

    key = f"menu/{datetime.utcnow().strftime('%Y%m%d')}/{enum_day.value}-{file.filename}"
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )
    s3_client.upload_fileobj(io.BytesIO(content), settings.s3_bucket, key, ExtraArgs={"ContentType": file.content_type})
    endpoint = str(settings.s3_endpoint_url).rstrip("/") if settings.s3_endpoint_url else ""
    url = f"{endpoint}/{settings.s3_bucket}/{key}" if endpoint else key

    service = _build_menu_service(session)
    week = await service.get_or_create_current_week()
    await service.set_day_photo(week, day=enum_day, url=url)
    payload = await service.serialize_week(week)
    try:
        day_payload = next(day for day in payload.days if day.name == enum_day.value)
    except StopIteration as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="День не найден") from exc
    return _serialize_menu_day(day_payload)


@router.post("/order-window", response_model=OrderWindowResponse)
async def set_order_window(
    request: OrderWindowRequest,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_session_dep),
) -> OrderWindowResponse:
    service = _build_order_window_service(session)
    week_start = request.weekStart
    if request.enabled and not week_start:
        today = datetime.utcnow().date()
        week_start = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
    window = await service.set_window(enabled=request.enabled, week_start=week_start)
    return OrderWindowResponse(enabled=window.next_week_enabled, weekStart=window.week_start)


@router.post("/broadcasts", response_model=BroadcastResponse)
async def create_broadcast(
    request: BroadcastRequest,
    admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_session_dep),
    redis: Redis | None = Depends(get_redis),
) -> BroadcastResponse:
    await _rate_limit_broadcasts(redis, str(admin.id))
    service = BroadcastService(session, redis=redis)
    broadcast = await service.enqueue_broadcast(channels=request.channels, html=request.html)
    return BroadcastResponse(id=str(broadcast.id), status=broadcast.status.value, sentAt=broadcast.sent_at)
