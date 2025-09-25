from __future__ import annotations

import os
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import broadcast_rate_limiter, get_current_admin, get_db
from app.api.v1.schemas.broadcasts import BroadcastRequest, BroadcastResponse
from app.api.v1.schemas.menu import MenuDayUpdateRequest, MenuItemPayload, MenuWeekRequest, MenuWeekResponse
from app.api.v1.schemas.order_window import OrderWindowRequest, OrderWindowResponse
from app.core.config import settings
from app.domain.menu.service import MenuService
from app.domain.order_window.service import OrderWindowService
from app.domain.broadcasts.service import BroadcastService

router = APIRouter(prefix="/admin", tags=["admin"])

MEDIA_ROOT = Path("storage/menu")
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def _serialize_menu(week_data: dict) -> MenuWeekResponse:
    return MenuWeekResponse(
        week_start=week_data["weekStart"],
        title=week_data["title"],
        is_published=week_data["isPublished"],
        hero_image_url=week_data.get("heroImageUrl"),
        items={
            day: [
                MenuItemPayload(title=item["title"], description=item.get("description"), photo_url=item.get("photoUrl"))
                for item in items
            ]
            for day, items in week_data["items"].items()
        },
    )


@router.put("/menu/week", response_model=MenuWeekResponse)
async def upsert_menu_week(
    payload: MenuWeekRequest,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
) -> MenuWeekResponse:
    menu_service = MenuService(session)
    week = await menu_service.get_or_create_week(payload.week_start, title=payload.title)
    if payload.publish is not None:
        week.is_published = payload.publish
    await session.commit()
    _, items = await menu_service.list_week_menu(payload.week_start)
    return _serialize_menu(menu_service.serialize_week(week, items))


@router.put("/menu/{day}", response_model=MenuWeekResponse)
async def update_menu_day(
    day: str,
    payload: MenuDayUpdateRequest,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
) -> MenuWeekResponse:
    menu_service = MenuService(session)
    week = await menu_service.get_or_create_week(payload.week_start)
    items = await menu_service.set_day_items(
        week,
        day=day,
        items=[item.model_dump() for item in payload.items],
    )
    await session.commit()
    _, items_by_day = await menu_service.list_week_menu(payload.week_start)
    return _serialize_menu(menu_service.serialize_week(week, items_by_day))


@router.post("/menu/photo")
async def upload_menu_photo(
    file: UploadFile = File(...),
    _: None = Depends(get_current_admin),
) -> dict[str, str]:
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл слишком большой")
    suffix = Path(file.filename or "menu.jpg").suffix
    file_id = uuid.uuid4().hex
    target_path = MEDIA_ROOT / f"{file_id}{suffix}"
    contents = await file.read()
    target_path.write_bytes(contents)
    url = f"{settings.backend_url}/media/menu/{target_path.name}"
    # TODO: Replace local storage with MinIO/S3 upload per roadmap.
    return {"url": url}


@router.post("/order-window", response_model=OrderWindowResponse)
async def configure_order_window(
    payload: OrderWindowRequest,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(get_current_admin),
) -> OrderWindowResponse:
    service = OrderWindowService(session)
    window = await service.set_window(
        enabled=payload.enabled,
        week_start=payload.week_start,
        note=payload.note,
    )
    await session.commit()
    return OrderWindowResponse(
        is_enabled=window.is_enabled,
        week_start=window.week_start,
        note=window.note,
        updated_at=window.updated_at,
    )


@router.post("/broadcasts", response_model=BroadcastResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_broadcast(
    payload: BroadcastRequest,
    session: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin),
    _: None = Depends(broadcast_rate_limiter),
) -> BroadcastResponse:
    service = BroadcastService(session)
    broadcast = await service.schedule(
        author_id=admin.id,
        channels=payload.channels,
        html_body=payload.html,
        subject=payload.subject,
    )
    await session.commit()
    return BroadcastResponse(
        id=broadcast.id,
        status=broadcast.status,
        sent=broadcast.sent,
        failed=broadcast.failed,
        created_at=broadcast.created_at,
    )
