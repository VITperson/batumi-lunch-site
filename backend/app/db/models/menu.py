from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import DayOfferStatus, DayOfWeek


class MenuWeek(TimestampMixin, Base):
    __tablename__ = "menu_weeks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_label: Mapped[str] = mapped_column(String(128), nullable=False)
    week_start: Mapped[date | None] = mapped_column(Date, unique=True, nullable=True)
    is_current: Mapped[bool] = mapped_column(default=False)
    day_photos: Mapped[dict[str, str] | None] = mapped_column(JSON, default=dict)

    items: Mapped[list["MenuItem"]] = relationship("MenuItem", back_populates="week", cascade="all, delete-orphan")
    offers: Mapped[list["DayOffer"]] = relationship("DayOffer", back_populates="week", cascade="all, delete-orphan")


class DayOffer(TimestampMixin, Base):
    __tablename__ = "day_offers"
    __table_args__ = (UniqueConstraint("week_id", "day_of_week", name="uq_day_offers_week_day"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_weeks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_of_week: Mapped[DayOfWeek] = mapped_column(
        Enum(
            DayOfWeek,
            name="day_offer_day_of_week",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    status: Mapped[DayOfferStatus] = mapped_column(
        Enum(
            DayOfferStatus,
            name="day_offer_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=DayOfferStatus.AVAILABLE,
        nullable=False,
    )
    price_amount: Mapped[int] = mapped_column(Integer, default=1500, nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), default="GEL", nullable=False)
    portion_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    portions_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allergens: Mapped[list[str]] = mapped_column(JSON, default=list)
    badge: Mapped[str | None] = mapped_column(String(50), nullable=True)
    order_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    week: Mapped[MenuWeek] = relationship("MenuWeek", back_populates="offers")


class MenuItem(TimestampMixin, Base):
    __tablename__ = "menu_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("menu_weeks.id", ondelete="CASCADE"), index=True)
    day_of_week: Mapped[DayOfWeek] = mapped_column(
        Enum(
            DayOfWeek,
            name="menu_day_of_week",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    week: Mapped[MenuWeek] = relationship("MenuWeek", back_populates="items")


__all__ = ["MenuWeek", "MenuItem", "DayOffer"]
