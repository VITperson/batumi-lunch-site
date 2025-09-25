"""User management domain service."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.models.user import User
from app.db.models.enums import UserRole


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_telegram(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def ensure_admin(self, *, email: str, password: str | None = None) -> User:
        user = await self.get_by_email(email)
        if user is None:
            user = User(email=email, roles=[UserRole.admin.value], password_hash=self._hash(password))
            self.session.add(user)
        else:
            if UserRole.admin.value not in (user.roles or []):
                roles = list(user.roles or [])
                roles.append(UserRole.admin.value)
                user.roles = roles
            if password:
                user.password_hash = self._hash(password)
        await self.session.flush()
        return user

    async def create_user(
        self,
        *,
        email: str | None,
        password: str | None,
        telegram_id: int | None,
        full_name: str | None = None,
        roles: Optional[list[str]] = None,
    ) -> User:
        user = User(
            email=email,
            telegram_id=telegram_id,
            full_name=full_name,
            roles=roles or [UserRole.customer.value],
            password_hash=self._hash(password) if password else None,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await self.get_by_email(email)
        if not user or not user.password_hash:
            return None
        if verify_password(password, user.password_hash):
            return user
        return None

    def _hash(self, password: str | None) -> str | None:
        if not password:
            return None
        return hash_password(password)
