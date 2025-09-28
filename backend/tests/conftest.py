from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base


@pytest.fixture(scope="session")
def event_loop() -> AsyncIterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture()
async def async_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture()
def now() -> datetime:
    return datetime.utcnow()
