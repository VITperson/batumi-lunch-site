from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session_dep
from app.core.security import TokenType, create_access_token, create_refresh_token, decode_token
from app.db.models.user import User
from app.domain.users import InvalidCredentialsError, UserAlreadyExistsError, UserService

from ..schemas.auth import (
    LoginRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session_dep)) -> TokenResponse:
    service = UserService(session)
    user = await service.authenticate(email=request.email, password=request.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    return TokenResponse(
        accessToken=create_access_token(str(user.id)),
        refreshToken=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    try:
        payload = decode_token(request.refreshToken, expected_type=TokenType.REFRESH)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from None
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return TokenResponse(
        accessToken=create_access_token(subject),
        refreshToken=create_refresh_token(subject),
    )


def _serialize_user(user: User) -> ProfileResponse:
    return ProfileResponse(
        id=str(user.id),
        email=user.email,
        fullName=user.full_name,
        phone=user.phone,
        address=user.address,
        role=user.role.value,
    )


@router.get("/me", response_model=ProfileResponse)
async def me(current_user: User = Depends(get_current_user)) -> ProfileResponse:
    return _serialize_user(current_user)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_session_dep)) -> TokenResponse:
    service = UserService(session)
    try:
        user = await service.create_user(
            email=request.email,
            password=request.password,
            full_name=request.fullName,
            phone=request.phone,
            address=request.address,
        )
    except UserAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email уже зарегистрирован") from None

    return TokenResponse(
        accessToken=create_access_token(str(user.id)),
        refreshToken=create_refresh_token(str(user.id)),
    )


@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dep),
) -> ProfileResponse:
    service = UserService(session)

    if request.newPassword:
        if not request.currentPassword:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Укажите текущий пароль для смены пароля",
            )
        try:
            await service.change_password(
                current_user,
                current_password=request.currentPassword,
                new_password=request.newPassword,
            )
        except InvalidCredentialsError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный текущий пароль") from None

    await service.update_profile(
        current_user,
        full_name=request.fullName,
        phone=request.phone,
        address=request.address,
    )

    return _serialize_user(current_user)
