from __future__ import annotations

from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.broadcast import Broadcast, BroadcastStatus


class BroadcastService:
    def __init__(self, session: AsyncSession, redis: Redis | None = None) -> None:
        self.session = session
        self.redis = redis

    async def enqueue_broadcast(self, *, channels: list[str], html: str) -> Broadcast:
        broadcast = Broadcast(channels=channels, html=html, status=BroadcastStatus.PENDING)
        self.session.add(broadcast)
        await self.session.flush()
        # TODO: push job to worker queue (RQ/Celery) once workers are wired
        return broadcast

    async def mark_running(self, broadcast: Broadcast) -> Broadcast:
        broadcast.status = BroadcastStatus.RUNNING
        await self.session.flush()
        return broadcast

    async def mark_completed(self, broadcast: Broadcast) -> Broadcast:
        broadcast.status = BroadcastStatus.COMPLETED
        broadcast.sent_at = datetime.utcnow()
        await self.session.flush()
        return broadcast

    async def mark_failed(self, broadcast: Broadcast, reason: str) -> Broadcast:
        broadcast.status = BroadcastStatus.FAILED
        broadcast.failed_reason = reason
        await self.session.flush()
        return broadcast


__all__ = ["BroadcastService"]
