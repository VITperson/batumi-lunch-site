from __future__ import annotations

import secrets
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from redis.asyncio import Redis
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models.enums import DayOfferStatus, DayOfWeek, OrderStatus, UserRole
from app.db.models.menu import DayOffer, MenuItem, MenuWeek
from app.db.models.order import Order
from app.db.models.order_template import OrderTemplate, OrderTemplateWeek
from app.db.models.user import User

from ..menu import MenuService
from ..order_window import DayAvailability, OrderWindowService
from .errors import (
    DuplicateOrderError,
    ForbiddenOrderActionError,
    OrderNotFoundError,
    OrderWindowClosedError,
    ValidationError,
)

_ACTIVE_STATUSES = {OrderStatus.NEW, OrderStatus.CONFIRMED}


@dataclass(slots=True)
class OrderDraft:
    day: DayOfWeek
    count: int
    address: str
    phone: str | None


@dataclass(slots=True)
class PlannerSelection:
    offer_id: uuid.UUID
    portions: int


@dataclass(slots=True)
class PlannerWeekRequest:
    week_start: date | None
    selections: list[PlannerSelection]
    enabled: bool = True


@dataclass(slots=True)
class PlannerWeekQuote:
    week_start: date | None
    week_label: str | None
    enabled: bool
    menu_status: str
    items: list[PlannerLine]
    subtotal: int
    currency: str | None
    warnings: list[str]


@dataclass(slots=True)
class PlannerLine:
    offer_id: uuid.UUID
    day: str
    status: str
    requested_portions: int
    accepted_portions: int
    unit_price: int
    currency: str
    subtotal: int
    message: str | None


@dataclass(slots=True)
class PlannerQuote:
    items: list[PlannerLine]
    subtotal: int
    discount: int
    total: int
    currency: str
    warnings: list[str]
    promo_code: str | None
    promo_code_error: str | None
    delivery_zone: str | None
    delivery_available: bool
    weeks: list[PlannerWeekQuote]


@dataclass(slots=True)
class PlannerCheckoutWeek:
    index: int
    week_start: date | None
    label: str | None
    enabled: bool
    menu_status: str
    subtotal: int
    currency: str | None
    warnings: list[str]


@dataclass(slots=True)
class PlannerCheckoutResult:
    template_id: uuid.UUID
    subtotal: int
    discount: int
    total: int
    currency: str
    promo_code: str | None
    delivery_zone: str | None
    delivery_available: bool
    weeks: list[PlannerCheckoutWeek]


_PROMO_CODES: dict[str, dict[str, int | str]] = {
    "WELCOME10": {"type": "percent", "value": 10, "min_subtotal": 3000},
    "TRYWEEK": {"type": "flat", "value": 1500, "min_subtotal": 1500},
}

_DELIVERY_ZONES: dict[str, tuple[str, ...]] = {
    "batumi-center": (
        "батум",
        "batumi",
        "чавчавадзе",
        "гогебашвили",
        "чкхетидзе",
        "гурам",
        "old boulevard",
    ),
    "new-boulevard": (
        "агмашенебели",
        "бульвар",
        "alliance",
        "orbi",
        "sunny beach",
    ),
}


class OrderService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        menu_service: MenuService,
        window_service: OrderWindowService,
        redis: Redis | None = None,
    ) -> None:
        self.session = session
        self.menu_service = menu_service
        self.window_service = window_service
        self.redis = redis

    async def _rate_limit(self, *, user: User) -> None:
        if not self.redis:
            return
        key = f"{settings.orders_rate_limit_redis_key_prefix}:{user.id}"
        ttl = await self.redis.ttl(key)
        if ttl and ttl > 0:
            raise ValidationError(
                field="rate_limit",
                message="Слишком часто: подождите перед следующим заказом",
            )
        await self.redis.set(key, "1", ex=settings.order_rate_limit_window_seconds)

    async def _ensure_menu(self, *, day: DayOfWeek, target_week_start: date) -> tuple[MenuWeek, list[str]]:
        week = await self.menu_service.get_week(week_start=target_week_start, fallback=False)
        if not week:
            raise ValidationError(field="day", message="Меню для выбранной недели не опубликовано")

        stmt = (
            select(MenuItem)
            .where(and_(MenuItem.week_id == week.id, MenuItem.day_of_week == day))
            .order_by(MenuItem.position)
        )
        rows = await self.session.execute(stmt)
        items = [row.title for row in rows.scalars()]
        if not items:
            raise ValidationError(field="day", message="Меню на выбранный день не заполнено")
        return week, items

    async def _find_duplicate(self, *, user: User, day: DayOfWeek, target_week_start: date) -> Order | None:
        stmt = (
            select(Order)
            .where(
                and_(
                    Order.user_id == user.id,
                    Order.day_of_week == day,
                    Order.delivery_week_start == target_week_start,
                    Order.status.in_(list(_ACTIVE_STATUSES)),
                )
            )
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_order(self, *, user: User, draft: OrderDraft) -> Order:
        if draft.count < 1 or draft.count > settings.order_daily_limit:
            raise ValidationError(
                field="count",
                message=f"Количество должно быть от 1 до {settings.order_daily_limit}",
            )
        if not draft.address.strip():
            raise ValidationError(field="address", message="Адрес доставки обязателен")

        await self._rate_limit(user=user)

        availability: DayAvailability = await self.window_service.evaluate_day(draft.day.value)
        if not availability.allowed:
            raise OrderWindowClosedError(availability.warning or "День недоступен")

        _, menu_items = await self._ensure_menu(day=draft.day, target_week_start=availability.target_week_start)

        duplicate = await self._find_duplicate(user=user, day=draft.day, target_week_start=availability.target_week_start)
        if duplicate:
            raise DuplicateOrderError(
                existing_order_id=duplicate.id,
                existing_count=duplicate.count,
                day=draft.day.value,
            )

        delivery_date = availability.target_week_start + timedelta(days=_day_offset(draft.day))
        order = Order(
            id=_generate_order_id(user.id),
            user_id=user.id,
            day_of_week=draft.day,
            count=draft.count,
            menu_items=menu_items,
            status=OrderStatus.NEW,
            address=draft.address.strip(),
            phone=draft.phone,
            delivery_week_start=availability.target_week_start,
            delivery_date=delivery_date,
            next_week=availability.is_next_week,
            unit_price=settings.order_price_lari,
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def calculate_planner_quote(
        self,
        *,
        selections: list[PlannerSelection],
        promo_code: str | None = None,
        address: str | None = None,
        weeks: list[PlannerWeekRequest] | None = None,
    ) -> PlannerQuote:
        week_requests = self._normalize_week_requests(selections, weeks)
        return await self._build_planner_quote(
            week_requests=week_requests,
            promo_code=promo_code,
            address=address,
        )

    async def create_planner_template(
        self,
        *,
        user: User | None,
        selections: list[PlannerSelection],
        weeks: list[PlannerWeekRequest] | None,
        address: str,
        promo_code: str | None = None,
        repeat_weeks: bool = True,
        weeks_count: int = 1,
    ) -> PlannerCheckoutResult:
        normalized_address = address.strip()
        if not normalized_address:
            raise ValidationError(field="address", message="Адрес доставки обязателен")

        week_requests = self._normalize_week_requests(selections, weeks)
        quote = await self._build_planner_quote(
            week_requests=week_requests,
            promo_code=promo_code,
            address=normalized_address,
        )

        has_enabled_items = any(week.enabled and week.items for week in quote.weeks)
        if not has_enabled_items:
            raise ValidationError(field="selections", message="Выберите хотя бы один день для заказа")

        stored_weeks_count = max(len(week_requests), weeks_count)
        template = OrderTemplate(
            user_id=user.id if user else None,
            base_week_start=week_requests[0].week_start if week_requests else None,
            weeks_count=stored_weeks_count,
            repeat_weeks=repeat_weeks,
            address=normalized_address,
            promo_code=quote.promo_code,
            subtotal=quote.subtotal,
            discount=quote.discount,
            total=quote.total,
            currency=quote.currency,
            delivery_zone=quote.delivery_zone,
            delivery_available=quote.delivery_available,
        )
        self.session.add(template)
        await self.session.flush()

        for index, (request, week_quote) in enumerate(zip(week_requests, quote.weeks)):
            selections_payload = [
                {"offerId": str(selection.offer_id), "portions": selection.portions}
                for selection in request.selections
            ]
            items_payload = [
                {
                    "offerId": str(item.offer_id),
                    "day": item.day,
                    "status": item.status,
                    "requestedPortions": item.requested_portions,
                    "acceptedPortions": item.accepted_portions,
                    "unitPrice": item.unit_price,
                    "currency": item.currency,
                    "subtotal": item.subtotal,
                    "message": item.message,
                }
                for item in week_quote.items
            ]
            week_row = OrderTemplateWeek(
                template_id=template.id,
                week_index=index,
                week_start=request.week_start,
                enabled=week_quote.enabled,
                menu_status=week_quote.menu_status,
                label=week_quote.week_label,
                subtotal=week_quote.subtotal,
                currency=week_quote.currency,
                selections=selections_payload,
                items=items_payload,
                warnings=week_quote.warnings,
            )
            self.session.add(week_row)

        await self.session.flush()

        weeks_summary = [
            PlannerCheckoutWeek(
                index=index,
                week_start=week.week_start,
                label=week.week_label,
                enabled=week.enabled,
                menu_status=week.menu_status,
                subtotal=week.subtotal,
                currency=week.currency,
                warnings=week.warnings,
            )
            for index, week in enumerate(quote.weeks)
        ]

        return PlannerCheckoutResult(
            template_id=template.id,
            subtotal=quote.subtotal,
            discount=quote.discount,
            total=quote.total,
            currency=quote.currency,
            promo_code=quote.promo_code,
            delivery_zone=quote.delivery_zone,
            delivery_available=quote.delivery_available,
            weeks=weeks_summary,
        )

    def _normalize_week_requests(
        self,
        selections: list[PlannerSelection],
        weeks: list[PlannerWeekRequest] | None,
    ) -> list[PlannerWeekRequest]:
        if weeks:
            return [
                PlannerWeekRequest(
                    week_start=week.week_start,
                    selections=list(week.selections),
                    enabled=week.enabled,
                )
                for week in weeks
            ]
        return [PlannerWeekRequest(week_start=None, selections=selections, enabled=True)]

    async def _build_planner_quote(
        self,
        *,
        week_requests: list[PlannerWeekRequest],
        promo_code: str | None,
        address: str | None,
    ) -> PlannerQuote:
        if not week_requests:
            week_requests = [PlannerWeekRequest(week_start=None, selections=[], enabled=True)]

        week_quotes = await self._calculate_multi_week_quotes(week_requests)

        subtotal = sum(week.subtotal for week in week_quotes if week.enabled)
        discount, applied_code, promo_error = _apply_promo_code(subtotal, promo_code)
        total = max(subtotal - discount, 0)

        zone, delivery_available, zone_message = _detect_zone(address)

        warnings: list[str] = []
        for week in week_quotes:
            warnings.extend(week.warnings)
        if promo_error:
            warnings.append(promo_error)
        if zone_message:
            warnings.append(zone_message)

        primary_week = _resolve_primary_week(week_quotes)
        items = primary_week.items if primary_week else []
        currency = _resolve_currency(week_quotes)

        return PlannerQuote(
            items=items,
            subtotal=subtotal,
            discount=discount,
            total=total,
            currency=currency,
            warnings=warnings,
            promo_code=applied_code,
            promo_code_error=promo_error,
            delivery_zone=zone,
            delivery_available=delivery_available,
            weeks=week_quotes,
        )

    async def _calculate_multi_week_quotes(self, requests: list[PlannerWeekRequest]) -> list[PlannerWeekQuote]:
        if not requests:
            return []

        offer_ids: set[uuid.UUID] = set()
        for request in requests:
            if not request.enabled:
                continue
            for selection in request.selections:
                if selection.portions > 0:
                    offer_ids.add(selection.offer_id)

        offers: dict[uuid.UUID, DayOffer] = {}
        if offer_ids:
            stmt = select(DayOffer).options(selectinload(DayOffer.week)).where(DayOffer.id.in_(offer_ids))
            offers_result = await self.session.execute(stmt)
            offers = {offer.id: offer for offer in offers_result.scalars()}

        week_starts = {request.week_start for request in requests if request.week_start}
        weeks_map: dict[date, MenuWeek] = {}
        if week_starts:
            stmt_weeks = select(MenuWeek).where(MenuWeek.week_start.in_(week_starts))
            weeks_result = await self.session.execute(stmt_weeks)
            weeks_map = {week.week_start: week for week in weeks_result.scalars() if week.week_start}

        quotes: list[PlannerWeekQuote] = []
        for request in requests:
            quotes.append(_build_week_quote(request, offers, weeks_map))
        return quotes

    async def list_orders_for_user(self, *, user: User) -> list[Order]:
        stmt = select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def list_orders_for_week(self, *, week_start: date) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.delivery_week_start == week_start)
            .order_by(Order.day_of_week, Order.created_at)
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def update_order_count(self, *, order_id: str, new_count: int, actor: User) -> Order:
        order = await self.session.get(Order, order_id)
        if not order:
            raise OrderNotFoundError(order_id)
        if actor.role != UserRole.ADMIN and order.user_id != actor.id:
            raise ForbiddenOrderActionError(order_id, "Нет доступа для изменения заказа")
        if order.status not in _ACTIVE_STATUSES:
            raise ForbiddenOrderActionError(order_id, "Заказ уже в обработке")
        if new_count < 1 or new_count > settings.order_daily_limit:
            raise ValidationError(field="count", message=f"Количество должно быть от 1 до {settings.order_daily_limit}")
        order.count = new_count
        await self.session.flush()
        return order

    async def cancel_order(self, *, order_id: str, actor: User, reason: str | None = None) -> Order:
        order = await self.session.get(Order, order_id)
        if not order:
            raise OrderNotFoundError(order_id)
        if actor.role != UserRole.ADMIN and order.user_id != actor.id:
            raise ForbiddenOrderActionError(order_id, "Нет доступа для отмены заказа")
        if order.status not in _ACTIVE_STATUSES:
            raise ForbiddenOrderActionError(order_id, "Заказ уже обработан")
        order.status = OrderStatus.CANCELLED if actor.role == UserRole.ADMIN else OrderStatus.CANCELLED_BY_USER
        await self.session.flush()
        return order


def _build_week_quote(
    request: PlannerWeekRequest,
    offers: dict[uuid.UUID, DayOffer],
    weeks_map: dict[date, MenuWeek],
) -> PlannerWeekQuote:
    week_label = _resolve_week_label(request.week_start, weeks_map)

    if not request.enabled:
        return PlannerWeekQuote(
            week_start=request.week_start,
            week_label=week_label,
            enabled=False,
            menu_status="disabled",
            items=[],
            subtotal=0,
            currency=None,
            warnings=[],
        )

    aggregated: Counter[uuid.UUID] = Counter()
    for selection in request.selections:
        if selection.portions > 0:
            aggregated[selection.offer_id] += selection.portions

    has_menu_row = request.week_start is not None and request.week_start in weeks_map
    is_pending_menu = request.week_start is not None and not has_menu_row

    if not aggregated:
        menu_status = "empty" if has_menu_row else "pending"
        return PlannerWeekQuote(
            week_start=request.week_start,
            week_label=week_label,
            enabled=True,
            menu_status=menu_status,
            items=[],
            subtotal=0,
            currency=None,
            warnings=[],
        )

    items: list[PlannerLine] = []
    warnings: list[str] = []
    subtotal = 0
    currency: str | None = None
    menu_status = "pending" if not has_menu_row else "published"

    for offer_id, requested in aggregated.items():
        offer = offers.get(offer_id)
        if not offer:
            message = "Предложение больше недоступно"
            warnings.append(message)
            items.append(
                PlannerLine(
                    offer_id=offer_id,
                    day="",
                    status="missing",
                    requested_portions=requested,
                    accepted_portions=0,
                    unit_price=0,
                    currency=currency or "GEL",
                    subtotal=0,
                    message=message,
                )
            )
            continue

        offer_week_start = offer.week.week_start if offer.week else None
        if request.week_start and offer_week_start and offer_week_start != request.week_start:
            if is_pending_menu:
                currency = offer.price_currency
                subtotal += requested * offer.price_amount
                items.append(
                    PlannerLine(
                        offer_id=offer.id,
                        day=offer.day_of_week.value,
                        status="reserved",
                        requested_portions=requested,
                        accepted_portions=requested,
                        unit_price=offer.price_amount,
                        currency=offer.price_currency,
                        subtotal=requested * offer.price_amount,
                        message="Меню уточняется: закрепили текущую цену",
                    )
                )
                continue

            message = "Предложение относится к другой неделе"
            warnings.append(message)
            items.append(
                PlannerLine(
                    offer_id=offer.id,
                    day=offer.day_of_week.value,
                    status="missing",
                    requested_portions=requested,
                    accepted_portions=0,
                    unit_price=0,
                    currency=currency or offer.price_currency,
                    subtotal=0,
                    message=message,
                )
            )
            continue

        currency = offer.price_currency
        available_capacity = None
        if offer.portion_limit is not None:
            available_capacity = max(offer.portion_limit - offer.portions_reserved, 0)

        accepted = requested
        status = "ok"
        message: str | None = None

        if offer.status != DayOfferStatus.AVAILABLE:
            status = offer.status.value
            accepted = 0
            message = "День недоступен для заказа"
        elif available_capacity is not None:
            if available_capacity <= 0:
                status = "sold_out"
                accepted = 0
                message = "Все порции на этот день уже забронированы"
            elif requested > available_capacity:
                status = "partial"
                accepted = available_capacity
                message = f"Доступно только {available_capacity} порций"

        line_subtotal = accepted * offer.price_amount
        subtotal += line_subtotal
        if message:
            warnings.append(message)

        items.append(
            PlannerLine(
                offer_id=offer.id,
                day=offer.day_of_week.value,
                status=status,
                requested_portions=requested,
                accepted_portions=accepted,
                unit_price=offer.price_amount,
                currency=offer.price_currency,
                subtotal=line_subtotal,
                message=message,
            )
        )

        if menu_status == "pending":
            menu_status = "published"

    return PlannerWeekQuote(
        week_start=request.week_start,
        week_label=week_label,
        enabled=True,
        menu_status=menu_status,
        items=items,
        subtotal=subtotal,
        currency=currency,
        warnings=warnings,
    )


def _resolve_primary_week(weeks: list[PlannerWeekQuote]) -> PlannerWeekQuote | None:
    for week in weeks:
        if week.enabled:
            return week
    return weeks[0] if weeks else None


def _resolve_currency(weeks: list[PlannerWeekQuote]) -> str:
    for week in weeks:
        if week.currency:
            return week.currency
    return "GEL"


def _resolve_week_label(week_start: date | None, weeks_map: dict[date, MenuWeek]) -> str | None:
    if not week_start:
        return None
    week = weeks_map.get(week_start)
    if week and week.week_label:
        return week.week_label
    return _format_week_label(week_start)


def _format_week_label(week_start: date | None) -> str | None:
    if not week_start:
        return None
    return week_start.strftime("%d.%m.%Y")


def _generate_order_id(user_pk: uuid.UUID | str | int) -> str:
    if isinstance(user_pk, uuid.UUID):
        user_val = user_pk.int
    else:
        user_val = int(user_pk)
    timestamp = _base36(int(time.time()))
    uid36 = _base36(abs(user_val))[-4:].rjust(4, "0")
    rnd = _base36(secrets.randbits(20)).rjust(4, "0")[:4]
    return f"BLB-{timestamp}-{uid36}-{rnd}"


def _base36(value: int) -> str:
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if value == 0:
        return "0"
    neg = value < 0
    value = abs(value)
    result = []
    while value:
        value, digit = divmod(value, 36)
        result.append(alphabet[digit])
    if neg:
        result.append("-")
    return "".join(reversed(result))


def _apply_promo_code(subtotal: int, promo_code: str | None) -> tuple[int, str | None, str | None]:
    if not promo_code:
        return 0, None, None

    normalized = promo_code.strip().upper()
    rule = _PROMO_CODES.get(normalized)
    if not rule:
        return 0, None, "Промокод не найден"

    min_subtotal = int(rule.get("min_subtotal", 0))
    if subtotal < min_subtotal:
        required_lari = min_subtotal / 100
        return 0, None, f"Минимальная сумма для промокода {normalized} — {required_lari:.0f} ₾"

    discount = 0
    if rule.get("type") == "percent":
        discount = subtotal * int(rule.get("value", 0)) // 100
    else:
        discount = int(rule.get("value", 0))

    discount = min(discount, subtotal)
    return discount, normalized, None


def _detect_zone(address: str | None) -> tuple[str | None, bool, str | None]:
    if not address:
        return None, False, "Укажите адрес, чтобы проверить доставку"

    normalized = address.lower()
    for zone, keywords in _DELIVERY_ZONES.items():
        if any(keyword in normalized for keyword in keywords):
            return zone, True, None

    return None, False, "Адрес пока вне зоны доставки (центр и новый бульвар)"


def _day_offset(day: DayOfWeek) -> int:
    mapping = {
        DayOfWeek.MONDAY: 0,
        DayOfWeek.TUESDAY: 1,
        DayOfWeek.WEDNESDAY: 2,
        DayOfWeek.THURSDAY: 3,
        DayOfWeek.FRIDAY: 4,
    }
    return mapping[day]


__all__ = [
    "OrderService",
    "OrderDraft",
    "PlannerSelection",
    "PlannerLine",
    "PlannerQuote",
    "PlannerWeekRequest",
    "PlannerWeekQuote",
    "PlannerCheckoutWeek",
    "PlannerCheckoutResult",
]
