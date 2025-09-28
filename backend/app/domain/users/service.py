from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.models.enums import UserRole
from app.db.models.user import User

from .errors import InvalidCredentialsError, UserAlreadyExistsError


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def ensure_user(self, *, email: str | None, telegram_id: int | None, full_name: str | None = None) -> User:
        if email:
            user = await self.get_by_email(email)
            if user:
                return user
        if telegram_id:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                return user
        user = User(email=email.lower() if email else None, telegram_id=telegram_id, full_name=full_name)
        self.session.add(user)
        await self.session.flush()
        return user

    async def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
        phone: str | None = None,
        address: str | None = None,
        role: UserRole = UserRole.CUSTOMER,
    ) -> User:
        normalized_email = email.lower()
        if await self.get_by_email(normalized_email):
            raise UserAlreadyExistsError(normalized_email)

        user = User(
            email=normalized_email,
            full_name=full_name,
            phone=phone,
            address=address,
            role=role,
            is_active=True,
        )
        user.password_hash = hash_password(password)
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_password(self, user: User, password: str) -> User:
        user.password_hash = hash_password(password)
        await self.session.flush()
        return user

    async def authenticate(self, *, email: str, password: str) -> User | None:
        user = await self.get_by_email(email)
        if not user or not user.password_hash:
            return None
        if not verify_password(password, user.password_hash):
            return None
        user.last_login_at = datetime.utcnow()
        await self.session.flush()
        return user

    async def update_profile(
        self,
        user: User,
        *,
        full_name: str | None = None,
        address: str | None = None,
        phone: str | None = None,
    ) -> User:
        if full_name is not None:
            user.full_name = full_name
        if address is not None:
            user.address = address
        if phone is not None:
            user.phone = phone
        await self.session.flush()
        return user

    async def promote_to_admin(self, user: User) -> User:
        user.role = UserRole.ADMIN
        await self.session.flush()
        return user

    async def change_password(self, user: User, *, current_password: str, new_password: str) -> User:
        if not user.password_hash or not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("invalid current password")
        user.password_hash = hash_password(new_password)
        await self.session.flush()
        return user


__all__ = ["UserService"]
