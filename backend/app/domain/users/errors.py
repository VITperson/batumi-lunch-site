from __future__ import annotations


class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an email that already exists."""

    def __init__(self, email: str) -> None:
        super().__init__(f"User with email {email} already exists")
        self.email = email


class InvalidCredentialsError(Exception):
    """Raised when provided credentials are invalid."""


__all__ = ["UserAlreadyExistsError", "InvalidCredentialsError"]
