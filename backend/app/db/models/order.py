from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import DayOfWeek, OrderStatus


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day_of_week: Mapped[DayOfWeek] = mapped_column(
        Enum(
            DayOfWeek,
            name="day_of_week",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        index=True,
    )
    count: Mapped[int] = mapped_column(Integer, default=1)
    menu_items: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            name="order_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=OrderStatus.NEW,
        index=True,
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delivery_week_start: Mapped[date] = mapped_column(Date, index=True)
    delivery_date: Mapped[date] = mapped_column(Date, index=True)
    next_week: Mapped[bool] = mapped_column(Boolean, default=False)
    unit_price: Mapped[int] = mapped_column(Integer, default=15)

    user = relationship("User", back_populates="orders")

    __table_args__ = (
        CheckConstraint("count >= 1", name="ck_orders_count_min"),
        CheckConstraint("count <= 12", name="ck_orders_count_max"),
    )


__all__ = ["Order"]
