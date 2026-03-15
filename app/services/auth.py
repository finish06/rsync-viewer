from datetime import timedelta
from typing import Any, Optional
from uuid import UUID

import hashlib
from uuid import uuid4

import bcrypt
import jwt

from app.config import get_settings
from app.utils import utc_now


# Role constants
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"

VALID_ROLES = {ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER}

# Role hierarchy: higher index = more permissions
ROLE_HIERARCHY = {
    ROLE_VIEWER: 0,
    ROLE_OPERATOR: 1,
    ROLE_ADMIN: 2,
}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def hash_token(token: str) -> str:
    """Hash a long token (e.g. JWT) using SHA-256 + bcrypt.

    bcrypt has a 72-byte input limit. JWT strings exceed this, so we
    SHA-256 the token first to get a fixed-length digest, then bcrypt that.
    """
    digest = hashlib.sha256(token.encode()).hexdigest()
    return bcrypt.hashpw(digest.encode(), bcrypt.gensalt()).decode()


def verify_token(token: str, token_hash: str) -> bool:
    """Verify a long token against its SHA-256 + bcrypt hash."""
    digest = hashlib.sha256(token.encode()).hexdigest()
    return bcrypt.checkpw(digest.encode(), token_hash.encode())


def role_at_least(user_role: str, minimum_role: str) -> bool:
    """Check if user_role is at or above minimum_role in hierarchy."""
    return ROLE_HIERARCHY.get(user_role, -1) >= ROLE_HIERARCHY.get(minimum_role, 999)


def create_access_token(
    user_id: UUID,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token with user claims."""
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_expiry_minutes)
    now = utc_now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: UUID,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token."""
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(days=settings.jwt_refresh_expiry_days)
    now = utc_now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises jwt.InvalidTokenError on failure."""
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )


# Password reset token expiry
PASSWORD_RESET_TOKEN_EXPIRY = timedelta(hours=1)


def is_last_admin(session: Any) -> bool:
    """Check if there is only one active admin user remaining."""
    from sqlmodel import func, select

    from app.models.user import User

    admin_count: int = session.exec(
        select(func.count()).where(User.role == ROLE_ADMIN, User.is_active.is_(True))  # type: ignore[attr-defined]
    ).one()
    return admin_count <= 1
