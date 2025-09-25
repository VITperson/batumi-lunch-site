from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.v1.schemas.menu import MenuWeekResponse, MenuItemPayload
from app.domain.menu.service import MenuService

router = APIRouter(prefix="/menu", tags=["menu"])


def _week_start_for(day: date | None) -> date:
    target = day or datetime.utcnow().date()
    return target - timedelta(days=target.weekday())


@router.get("/week", response_model=MenuWeekResponse)
async def get_menu_for_week(
    when: date | None = Query(default=None, description="Date to anchor week"),
    session: AsyncSession = Depends(get_db),
) -> MenuWeekResponse:
    week_start = _week_start_for(when)
    service = MenuService(session)
    week, items = await service.list_week_menu(week_start)
    if not week:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Меню не найдено")
    serialized = service.serialize_week(week, items)
    return MenuWeekResponse(
        week_start=serialized["weekStart"],
        title=serialized["title"],
        is_published=serialized["isPublished"],
        hero_image_url=serialized.get("heroImageUrl"),
        items={
            day: [
                MenuItemPayload(title=item["title"], description=item.get("description"), photo_url=item.get("photoUrl"))
                for item in items
            ]
            for day, items in serialized["items"].items()
        },
    )
