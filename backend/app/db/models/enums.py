from __future__ import annotations

import enum


class DayOfWeek(enum.StrEnum):
    MONDAY = "Понедельник"
    TUESDAY = "Вторник"
    WEDNESDAY = "Среда"
    THURSDAY = "Четверг"
    FRIDAY = "Пятница"


class OrderStatus(enum.StrEnum):
    NEW = "new"
    CONFIRMED = "confirmed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    CANCELLED_BY_USER = "cancelled_by_user"


class UserRole(enum.StrEnum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class DayOfferStatus(enum.StrEnum):
    AVAILABLE = "available"
    SOLD_OUT = "sold_out"
    CLOSED = "closed"


__all__ = ["DayOfWeek", "OrderStatus", "UserRole", "DayOfferStatus"]
