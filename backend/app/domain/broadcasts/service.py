"""Broadcast service handling admin announcements."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.broadcast import Broadcast


class BroadcastService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def schedule(
        self,
        *,
        author_id: uuid.UUID | None,
        channels: list[str],
        html_body: str,
        subject: str | None = None,
    ) -> Broadcast:
        broadcast = Broadcast(
            author_id=author_id,
            channels=channels or ["email"],
            html_body=html_body,
            subject=subject,
            status="scheduled",
        )
        self.session.add(broadcast)
        await self.session.flush()
        # NOTE: hooking workers/queues will be done separately; for now mark as pending.
        return broadcast

    async def mark_sent(self, broadcast: Broadcast, *, sent: int, failed: int) -> None:
        broadcast.sent = sent
        broadcast.failed = failed
        broadcast.status = "completed"
        broadcast.sent_at = datetime.now(timezone.utc)
        await self.session.flush()
