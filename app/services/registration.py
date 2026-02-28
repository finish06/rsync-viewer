"""Shared user registration logic (AC-008).

Both the HTMX form handler and the API endpoint delegate core
registration business rules to this service.
"""

import logging

from sqlmodel import Session, func, select

from app.models.user import User
from app.services.auth import ROLE_ADMIN, ROLE_VIEWER, hash_password

logger = logging.getLogger(__name__)


class RegistrationError(Exception):
    """Raised when registration fails due to a business rule violation."""

    def __init__(self, message: str, *, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def register_user(
    session: Session,
    *,
    username: str,
    email: str,
    password: str,
) -> User:
    """Validate uniqueness, determine role, and persist a new user.

    Parameters
    ----------
    session : Session
        Active database session (caller owns commit/rollback).
    username, email, password : str
        Already-validated user input (Pydantic ``UserCreate`` should
        be applied before calling this function).

    Returns
    -------
    User
        The newly created user (session is flushed but **not** committed
        so the caller can decide transaction boundary).

    Raises
    ------
    RegistrationError
        If username or email already exists.
    """
    # Check for duplicate username
    if session.exec(select(User).where(User.username == username)).first():
        raise RegistrationError("Username already exists")

    # Check for duplicate email
    if session.exec(select(User).where(User.email == email)).first():
        raise RegistrationError("Email already exists")

    # First user gets admin role; subsequent users get viewer
    user_count = session.exec(select(func.count()).select_from(User)).one()
    role = ROLE_ADMIN if user_count == 0 else ROLE_VIEWER

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(
        "User registered",
        extra={"user_id": str(user.id), "username": user.username, "role": user.role},
    )

    return user
