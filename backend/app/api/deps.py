"""FastAPI dependencies (db sessions, auth, rate limiting)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import set_trace_id
from app.core.security import TokenPayload, decode_token
from app.db import get_session
from app.db.models.user import User
from app.domain.users.service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


async def get_db() -> AsyncSession:
    async for session in get_session():
        yield session


async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен") from None
    if payload.type != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный тип токена")
    set_trace_id(payload.sub)
    user_id = uuid.UUID(payload.sub)
    user = await UserService(session).get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if "admin" not in (user.roles or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуется роль администратора")
    return user


class RateLimiter:
    def __init__(self, key_prefix: str, limit: int, window_seconds: int) -> None:
        self.key_prefix = key_prefix
        self.limit = limit
        self.window_seconds = window_seconds
        self.redis = aioredis.from_url(settings.redis_dsn, decode_responses=True)

    async def __call__(self, user: User = Depends(get_current_user)) -> None:
        key = f"{self.key_prefix}:{user.id}"
        now = datetime.now(timezone.utc)
        try:
            ttl = await self.redis.ttl(key)
            count = await self.redis.incr(key)
        except Exception:
            # Redis unavailable: skip limiting fail-open.
            return
        if ttl == -1:
            await self.redis.expire(key, self.window_seconds)
        if count > self.limit:
            retry_after = max(ttl, 0) if ttl > 0 else self.window_seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много запросов. Попробуйте позже.",
                headers={"Retry-After": str(retry_after)},
            )


order_rate_limiter = RateLimiter("rate:orders", limit=1, window_seconds=10)
broadcast_rate_limiter = RateLimiter("rate:broadcasts", limit=3, window_seconds=60)
