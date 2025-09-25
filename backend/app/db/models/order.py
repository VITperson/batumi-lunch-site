"""Order model."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import OrderStatus


class Order(Base):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"))
    menu_week_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menuweek.id", ondelete="SET NULL"), nullable=True
    )
    day: Mapped[str] = mapped_column(String(16))
    count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.new.value)
    menu_snapshot: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    address_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_snapshot: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delivery_week_start: Mapped[date] = mapped_column(Date)
    is_next_week: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="orders")
    menu_week = relationship("MenuWeek", backref="orders")

    __table_args__ = (
        Index("ix_orders_week_status", "delivery_week_start", "status"),
        Index("ix_orders_user_day_week", "user_id", "day", "delivery_week_start"),
    )
