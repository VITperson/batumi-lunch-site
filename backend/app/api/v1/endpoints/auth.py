from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_current_user, get_db
from app.api.v1.schemas.auth import AuthResponse, LoginRequest, TokenPair, UserMe
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.domain.users.service import UserService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, response: Response, session: AsyncSession = Depends(get_db)) -> AuthResponse:
    user_service = UserService(session)
    user = await user_service.authenticate(request.email, request.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    access = create_access_token(str(user.id), scopes=user.roles or [])
    refresh = create_refresh_token(str(user.id))

    response.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.jwt_refresh_ttl,
    )

    return AuthResponse(
        user_id=user.id,
        email=user.email,
        roles=user.roles or [],
        access=TokenPair(access_token=access, expires_in=settings.jwt_access_ttl),
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> AuthResponse:
    token = request.cookies.get("refresh_token")
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh токен отсутствует")
    payload = decode_token(token)
    if payload.type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Некорректный refresh токен")
    user = await UserService(session).get_by_id(uuid.UUID(payload.sub))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    access = create_access_token(str(user.id), scopes=user.roles or [])
    new_refresh = create_refresh_token(str(user.id))
    response.set_cookie(
        "refresh_token",
        new_refresh,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.jwt_refresh_ttl,
    )
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        roles=user.roles or [],
        access=TokenPair(access_token=access, expires_in=settings.jwt_access_ttl),
    )


@router.get("/me", response_model=UserMe)
async def me(user = Depends(get_current_user)) -> UserMe:  # type: ignore[no-untyped-def]
    return UserMe(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=user.roles or [],
        address=user.address,
        phone=user.phone,
        created_at=user.created_at,
    )
