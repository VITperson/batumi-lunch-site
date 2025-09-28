from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..core.config import settings

_DEFAULT_SQLITE_URL = "sqlite+aiosqlite:///./batumi_lunch.db"


def _build_engine() -> AsyncEngine:
    url = str(settings.database_url or _DEFAULT_SQLITE_URL)
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_async_engine(url, echo=settings.debug, connect_args=connect_args)


engine = _build_engine()
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


__all__ = ["engine", "async_session_factory", "get_session"]
