"""Domain exceptions for order workflows."""

from __future__ import annotations

from dataclasses import dataclass


class OrderError(Exception):
    """Base order-domain error."""


@dataclass(slots=True)
class OrderWindowClosedError(OrderError):
    day: str
    message: str


@dataclass(slots=True)
class DuplicateOrderError(OrderError):
    existing_order_id: str
    day: str
    week_start: str


class OrderValidationError(OrderError):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class OrderNotFoundError(OrderError):
    pass
