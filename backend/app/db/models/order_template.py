from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class OrderTemplate(TimestampMixin, Base):
    __tablename__ = "order_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    base_week_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    weeks_count: Mapped[int] = mapped_column(Integer, default=1)
    repeat_weeks: Mapped[bool] = mapped_column(Boolean, default=True)
    address: Mapped[str] = mapped_column(Text)
    promo_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    discount: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="GEL")
    delivery_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delivery_available: Mapped[bool] = mapped_column(Boolean, default=False)

    weeks: Mapped[list["OrderTemplateWeek"]] = relationship(
        "OrderTemplateWeek", back_populates="template", cascade="all, delete-orphan"
    )


class OrderTemplateWeek(TimestampMixin, Base):
    __tablename__ = "order_template_weeks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    week_index: Mapped[int] = mapped_column(Integer, default=0)
    week_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    menu_status: Mapped[str] = mapped_column(String(32), default="pending")
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    selections: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    items: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)

    template: Mapped[OrderTemplate] = relationship("OrderTemplate", back_populates="weeks")


__all__ = ["OrderTemplate", "OrderTemplateWeek"]
