"""Shared database enumerations."""

from __future__ import annotations

import enum


class Weekday(str, enum.Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"

    @classmethod
    def from_human(cls, value: str) -> "Weekday":
        prepared = value.strip().lower()
        mapping = {
            "понедельник": cls.monday,
            "вторник": cls.tuesday,
            "среда": cls.wednesday,
            "четверг": cls.thursday,
            "пятница": cls.friday,
        }
        return mapping.get(prepared, cls(prepared))


class OrderStatus(str, enum.Enum):
    new = "new"
    confirmed = "confirmed"
    delivered = "delivered"
    cancelled = "cancelled"
    cancelled_by_user = "cancelled_by_user"


class UserRole(str, enum.Enum):
    customer = "customer"
    admin = "admin"
