"""Security helpers: password hashing and JWT management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str
    scopes: list[str] = []

    @property
    def expires_at(self) -> datetime:
        return datetime.fromtimestamp(self.exp, tz=timezone.utc)


def hash_password(password: str) -> str:
    return pwd_context.hash(password + settings.password_pepper)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password + settings.password_pepper, hashed_password)
    except Exception:
        return False


def _create_token(subject: str, ttl_seconds: int, *, token_type: str, scopes: Optional[list[str]] = None) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "iat": int(now.timestamp()),
        "type": token_type,
        "scopes": scopes or [],
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, scopes: Optional[list[str]] = None) -> str:
    return _create_token(subject, settings.jwt_access_ttl, token_type="access", scopes=scopes)


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, settings.jwt_refresh_ttl, token_type="refresh")


def decode_token(token: str) -> TokenPayload:
    data = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    try:
        return TokenPayload(**data)
    except ValidationError as exc:
        raise jwt.InvalidTokenError("Invalid token payload") from exc


__all__ = [
    "TokenPayload",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
]
