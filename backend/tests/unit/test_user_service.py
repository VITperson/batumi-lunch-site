from __future__ import annotations

import pytest

from app.db.models.enums import UserRole
from app.domain.users import InvalidCredentialsError, UserAlreadyExistsError, UserService


@pytest.mark.asyncio
async def test_create_user_assigns_hash_and_defaults(session):
    service = UserService(session)

    user = await service.create_user(
        email="new.user@example.com",
        password="supersecret",
        full_name="New User",
        phone="+995500000000",
        address="Батуми, ул. Пример, 1",
    )

    assert user.email == "new.user@example.com"
    assert user.password_hash is not None
    assert user.role == UserRole.CUSTOMER
    assert user.full_name == "New User"
    assert user.phone == "+995500000000"
    assert user.address == "Батуми, ул. Пример, 1"


@pytest.mark.asyncio
async def test_create_user_raises_for_duplicate_email(session):
    service = UserService(session)
    await service.create_user(email="dup@example.com", password="secret123")

    with pytest.raises(UserAlreadyExistsError):
        await service.create_user(email="dup@example.com", password="othersecret")


@pytest.mark.asyncio
async def test_change_password_success(session):
    service = UserService(session)
    user = await service.create_user(email="change@example.com", password="oldpassword")

    await service.change_password(user, current_password="oldpassword", new_password="newpassword123")

    assert user.password_hash is not None
    # authenticate with new password
    authenticated = await service.authenticate(email="change@example.com", password="newpassword123")
    assert authenticated is not None


@pytest.mark.asyncio
async def test_change_password_invalid_current(session):
    service = UserService(session)
    user = await service.create_user(email="invalid@example.com", password="correctpass")

    with pytest.raises(InvalidCredentialsError):
        await service.change_password(user, current_password="wrongpass", new_password="newpass123")
