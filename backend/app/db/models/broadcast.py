from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class BroadcastStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Broadcast(TimestampMixin, Base):
    __tablename__ = "broadcasts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channels: Mapped[list[str]] = mapped_column(JSON, default=list)
    html: Mapped[str] = mapped_column(Text)
    status: Mapped[BroadcastStatus] = mapped_column(Enum(BroadcastStatus, name="broadcast_status"), default=BroadcastStatus.PENDING)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = ["Broadcast", "BroadcastStatus"]
