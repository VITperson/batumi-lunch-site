from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


PHONE_PATTERN = re.compile(r"^\+?[\d\s]+$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refreshToken: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    fullName: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        trimmed = value.strip()
        if not trimmed:
            return None
        if not PHONE_PATTERN.fullmatch(trimmed):
            raise ValueError("phone must contain only digits and spaces")
        return trimmed


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"


class ProfileResponse(BaseModel):
    id: str
    email: EmailStr | None
    fullName: str | None
    phone: str | None
    address: str | None
    role: str


class ProfileUpdateRequest(BaseModel):
    fullName: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    currentPassword: str | None = Field(default=None, min_length=8, max_length=128)
    newPassword: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        trimmed = value.strip()
        if not trimmed:
            return None
        if not PHONE_PATTERN.fullmatch(trimmed):
            raise ValueError("phone must contain only digits and spaces")
        return trimmed


__all__ = [
    "LoginRequest",
    "RefreshRequest",
    "RegisterRequest",
    "TokenResponse",
    "ProfileResponse",
    "ProfileUpdateRequest",
]
