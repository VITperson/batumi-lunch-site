from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    user_id: UUID
    email: EmailStr | None
    roles: list[str]
    access: TokenPair


class UserMe(BaseModel):
    id: UUID
    email: EmailStr | None
    full_name: str | None
    roles: list[str]
    address: str | None
    phone: str | None
    created_at: datetime
