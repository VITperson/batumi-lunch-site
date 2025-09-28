from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class OrderWindow(TimestampMixin, Base):
    __tablename__ = "order_windows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    next_week_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    week_start: Mapped[date | None] = mapped_column(Date, nullable=True)


__all__ = ["OrderWindow"]
