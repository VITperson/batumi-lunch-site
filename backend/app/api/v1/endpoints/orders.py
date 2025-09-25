from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, order_rate_limiter
from app.api.v1.schemas.orders import (
    OrderCancelRequest,
    OrderCreateRequest,
    OrderListResponse,
    OrderResponse,
    OrderUpdateRequest,
)
from app.domain.orders.errors import DuplicateOrderError, OrderNotFoundError, OrderValidationError, OrderWindowClosedError
from app.domain.orders.service import OrderCreateData, OrderService
from app.db.models.order import Order
from app.db.models.user import User

router = APIRouter(prefix="/orders", tags=["orders"])


def serialize_order(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        public_id=order.public_id,
        day=order.day,
        count=order.count,
        status=order.status,
        menu=list(order.menu_snapshot or []),
        address=order.address_snapshot,
        phone=order.phone_snapshot,
        delivery_week_start=order.delivery_week_start,
        is_next_week=order.is_next_week,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(order_rate_limiter),
) -> OrderResponse:
    service = OrderService(session)
    try:
        order = await service.create(
            user,
            OrderCreateData(
                day=payload.day,
                count=payload.count,
                address=payload.address,
                phone=payload.phone,
                week_start=payload.week_start,
            ),
        )
        await session.commit()
    except DuplicateOrderError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "У вас уже есть заказ на этот день",
                "orderId": exc.existing_order_id,
                "weekStart": exc.week_start,
            },
        ) from exc
    except OrderWindowClosedError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except OrderValidationError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    return serialize_order(order)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    mine: bool = Query(default=False),
    week: date | None = Query(default=None),
) -> OrderListResponse:
    service = OrderService(session)
    if mine or week is None:
        orders = await service.list_for_user(user)
    else:
        if "admin" not in (user.roles or []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуется роль администратора")
        orders = await service.list_for_week(week)
    return OrderListResponse(orders=[serialize_order(o) for o in orders])


@router.get("/{public_id}", response_model=OrderResponse)
async def get_order(public_id: str, session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> OrderResponse:
    service = OrderService(session)
    try:
        order = await service.get_by_public_id(public_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    if order.user_id != user.id and "admin" not in (user.roles or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    return serialize_order(order)


@router.patch("/{public_id}", response_model=OrderResponse)
async def update_order(
    public_id: str,
    payload: OrderUpdateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderResponse:
    payload_dict = payload.model_dump(exclude_unset=True)
    if not payload_dict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет данных для обновления")
    service = OrderService(session)
    try:
        order = await service.update(user, public_id, **payload_dict)
        await session.commit()
    except OrderValidationError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except OrderNotFoundError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return serialize_order(order)


@router.post("/{public_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    public_id: str,
    _: OrderCancelRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderResponse:
    service = OrderService(session)
    try:
        order = await service.cancel(user, public_id)
        await session.commit()
    except OrderValidationError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except OrderNotFoundError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return serialize_order(order)
