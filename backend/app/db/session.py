"""Database session and engine management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def get_engine() -> AsyncEngine:
    return create_async_engine(settings.database_url_async, future=True, pool_pre_ping=True)


async_engine: AsyncEngine = get_engine()
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
