from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import TokenType, decode_token
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.db.session import get_session

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
_redis_client: Redis | None = Redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None


async def get_session_dep() -> AsyncIterator[AsyncSession]:
    async with get_session() as session:
        yield session


async def get_redis() -> Redis | None:
    return _redis_client


async def get_current_user(
    token: str = Depends(_oauth2_scheme),
    session: AsyncSession = Depends(get_session_dep),
) -> User:
    try:
        payload = decode_token(token, expected_type=TokenType.ACCESS)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await session.get(User, subject)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


__all__ = ["get_session_dep", "get_current_user", "get_current_admin", "get_redis"]
