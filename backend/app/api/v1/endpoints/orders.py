from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_redis, get_session_dep
from app.db.models.enums import DayOfWeek, UserRole
from app.db.models.order import Order
from app.domain.menu import MenuService
from app.domain.order_window import OrderWindowService
from app.domain.orders import (
    DuplicateOrderError,
    ForbiddenOrderActionError,
    OrderDraft,
    OrderNotFoundError,
    OrderService,
    OrderWindowClosedError,
    PlannerCheckoutResult,
    PlannerSelection,
    PlannerWeekRequest,
    ValidationError,
)
from app.domain.users import UserService

from ..schemas.orders import (
    PlannerCheckoutRequest,
    PlannerCheckoutResponse,
    PlannerCheckoutWeekResponse,
    OrderCalcItemResponse,
    OrderCalcRequest,
    OrderCalcResponse,
    OrderCancelRequest,
    OrderCreateRequest,
    OrderListResponse,
    OrderResponse,
    OrderUpdateRequest,
    PlannerWeekQuoteResponse,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        day=order.day_of_week.value,
        count=order.count,
        menu=order.menu_items,
        status=order.status.value,
        address=order.address,
        phone=order.phone,
        deliveryWeekStart=order.delivery_week_start,
        deliveryDate=order.delivery_date,
        nextWeek=order.next_week,
        createdAt=order.created_at,
        updatedAt=order.updated_at,
    )


def _build_services(session: AsyncSession, redis: Redis | None = None) -> OrderService:
    menu_service = MenuService(session)
    window_service = OrderWindowService(session)
    return OrderService(session, menu_service=menu_service, window_service=window_service, redis=redis)


@router.post("/calc", response_model=OrderCalcResponse)
async def calculate_planner_order(
    request: OrderCalcRequest,
    session: AsyncSession = Depends(get_session_dep),
    redis: Redis | None = Depends(get_redis),
) -> OrderCalcResponse:
    order_service = _build_services(session, redis)
    selections = [
        PlannerSelection(offer_id=selection.offerId, portions=selection.portions)
        for selection in request.selections
    ]
    weeks = None
    if request.weeks is not None:
        weeks = [
            PlannerWeekRequest(
                week_start=week.weekStart,
                enabled=week.enabled,
                selections=[
                    PlannerSelection(offer_id=item.offerId, portions=item.portions)
                    for item in week.selections
                ],
            )
            for week in request.weeks
        ]
    quote = await order_service.calculate_planner_quote(
        selections=selections,
        promo_code=request.promoCode,
        address=request.address,
        weeks=weeks,
    )
    return OrderCalcResponse(
        items=[
            OrderCalcItemResponse(
                offerId=item.offer_id,
                day=item.day,
                status=item.status,
                requestedPortions=item.requested_portions,
                acceptedPortions=item.accepted_portions,
                unitPrice=item.unit_price,
                currency=item.currency,
                subtotal=item.subtotal,
                message=item.message,
            )
            for item in quote.items
        ],
        subtotal=quote.subtotal,
        discount=quote.discount,
        total=quote.total,
        currency=quote.currency,
        warnings=quote.warnings,
        promoCode=quote.promo_code,
        promoCodeError=quote.promo_code_error,
        deliveryZone=quote.delivery_zone,
        deliveryAvailable=quote.delivery_available,
        weeks=[
            PlannerWeekQuoteResponse(
                weekStart=week.week_start,
                label=week.week_label,
                enabled=week.enabled,
                menuStatus=week.menu_status,
                items=[
                    OrderCalcItemResponse(
                        offerId=item.offer_id,
                        day=item.day,
                        status=item.status,
                        requestedPortions=item.requested_portions,
                        acceptedPortions=item.accepted_portions,
                        unitPrice=item.unit_price,
                        currency=item.currency,
                        subtotal=item.subtotal,
                        message=item.message,
                    )
                    for item in week.items
                ],
                subtotal=week.subtotal,
                currency=week.currency,
                warnings=week.warnings,
            )
            for week in quote.weeks
        ],
    )


@router.post("/checkout", response_model=PlannerCheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout_planner_order(
    request: PlannerCheckoutRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dep),
    redis: Redis | None = Depends(get_redis),
) -> PlannerCheckoutResponse:
    order_service = _build_services(session, redis)
    user_service = UserService(session)

    selections = [
        PlannerSelection(offer_id=selection.offerId, portions=selection.portions)
        for selection in request.selections
    ]

    weeks = None
    if request.weeks is not None:
        weeks = [
            PlannerWeekRequest(
                week_start=week.weekStart,
                enabled=week.enabled,
                selections=[
                    PlannerSelection(offer_id=item.offerId, portions=item.portions)
                    for item in week.selections
                ],
            )
            for week in request.weeks
        ]

    try:
        result: PlannerCheckoutResult = await order_service.create_planner_template(
            user=user,
            selections=selections,
            weeks=weeks,
            address=request.address,
            promo_code=request.promoCode,
            repeat_weeks=request.repeatWeeks,
            weeks_count=request.weeksCount,
        )
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"field": err.field, "message": err.message},
        ) from err

    await user_service.update_profile(user, address=request.address)
    await session.flush()

    return PlannerCheckoutResponse(
        templateId=result.template_id,
        subtotal=result.subtotal,
        discount=result.discount,
        total=result.total,
        currency=result.currency,
        promoCode=result.promo_code,
        deliveryZone=result.delivery_zone,
        deliveryAvailable=result.delivery_available,
        weeks=[
            PlannerCheckoutWeekResponse(
                index=week.index,
                weekStart=week.week_start,
                label=week.label,
                enabled=week.enabled,
                menuStatus=week.menu_status,
                subtotal=week.subtotal,
                currency=week.currency,
                warnings=week.warnings,
            )
            for week in result.weeks
        ],
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: OrderCreateRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dep),
    redis: Redis | None = Depends(get_redis),
) -> OrderResponse:
    try:
        day = DayOfWeek(request.day)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный день недели") from exc

    order_service = _build_services(session, redis)
    user_service = UserService(session)

    draft = OrderDraft(day=day, count=request.count, address=request.address, phone=request.phone)

    try:
        order = await order_service.create_order(user=user, draft=draft)
    except DuplicateOrderError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_order",
                "orderId": err.existing_order_id,
                "count": err.existing_count,
                "day": err.day,
            },
        ) from err
    except OrderWindowClosedError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err.message) from err
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"field": err.field, "message": err.message},
        ) from err
    else:
        if request.weekStart and request.weekStart != order.delivery_week_start:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недоступная неделя заказа")

        await user_service.update_profile(user, address=request.address, phone=request.phone)
        await session.flush()
        await session.refresh(order, attribute_names=["created_at", "updated_at"])

        return _order_to_response(order)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    mine: int | None = Query(default=None),
    week: date | None = Query(default=None),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dep),
) -> OrderListResponse:
    order_service = _build_services(session)

    if mine == 1 or user.role != UserRole.ADMIN:
        orders = await order_service.list_orders_for_user(user=user)
        return OrderListResponse(orders=[_order_to_response(order) for order in orders])

    if week is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="week parameter required for admin view")

    orders = await order_service.list_orders_for_week(week_start=week)
    return OrderListResponse(orders=[_order_to_response(order) for order in orders])


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dep),
) -> OrderResponse:
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    if user.role != UserRole.ADMIN and order.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")
    return _order_to_response(order)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    request: OrderUpdateRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dep),
    redis: Redis | None = Depends(get_redis),
) -> OrderResponse:
    order_service = _build_services(session, redis)
    user_service = UserService(session)

    updated_order: Order | None = None

    if request.count is not None:
        try:
            updated_order = await order_service.update_order_count(order_id=order_id, new_count=request.count, actor=user)
        except OrderNotFoundError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден") from err
        except ForbiddenOrderActionError as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err.reason) from err
        except ValidationError as err:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"field": err.field, "message": err.message}) from err

    if request.address is not None:
        target_order = updated_order or await session.get(Order, order_id)
        if not target_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
        if user.role != UserRole.ADMIN and target_order.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа для изменения заказа")
        target_order.address = request.address
        await user_service.update_profile(user, address=request.address)
        updated_order = target_order

    if not updated_order:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет данных для обновления")

    await session.flush()
    await session.refresh(updated_order, attribute_names=["created_at", "updated_at"])

    return _order_to_response(updated_order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    request: OrderCancelRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dep),
    redis: Redis | None = Depends(get_redis),
) -> OrderResponse:
    order_service = _build_services(session, redis)
    try:
        order = await order_service.cancel_order(order_id=order_id, actor=user, reason=request.reason)
    except OrderNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден") from err
    except ForbiddenOrderActionError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err.reason) from err

    await session.flush()
    await session.refresh(order, attribute_names=["created_at", "updated_at"])

    return _order_to_response(order)
