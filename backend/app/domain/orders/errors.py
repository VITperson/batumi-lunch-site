from __future__ import annotations

from dataclasses import dataclass


class OrderDomainError(Exception):
    """Base class for order domain errors."""


@dataclass(slots=True)
class OrderWindowClosedError(OrderDomainError):
    message: str


@dataclass(slots=True)
class DuplicateOrderError(OrderDomainError):
    existing_order_id: str
    existing_count: int
    day: str


@dataclass(slots=True)
class OrderNotFoundError(OrderDomainError):
    order_id: str


@dataclass(slots=True)
class ForbiddenOrderActionError(OrderDomainError):
    order_id: str
    reason: str


@dataclass(slots=True)
class ValidationError(OrderDomainError):
    field: str
    message: str


__all__ = [
    "OrderDomainError",
    "OrderWindowClosedError",
    "DuplicateOrderError",
    "OrderNotFoundError",
    "ForbiddenOrderActionError",
    "ValidationError",
]
