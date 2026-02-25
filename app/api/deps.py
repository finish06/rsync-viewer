import logging
from datetime import timedelta
from typing import Annotated, Optional
from uuid import UUID

import bcrypt
import jwt as pyjwt
from fastapi import Cookie, Depends, HTTPException, Header, Request, status
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models.sync_log import ApiKey
from app.models.user import User
from app.utils import utc_now

logger = logging.getLogger(__name__)


def hash_api_key(key: str) -> str:
    """Hash API key using bcrypt."""
    return bcrypt.hashpw(key.encode(), bcrypt.gensalt()).decode()


def verify_api_key_hash(key: str, hashed: str) -> bool:
    """Verify an API key against its bcrypt hash."""
    return bcrypt.checkpw(key.encode(), hashed.encode())


async def verify_api_key(
    x_api_key: Annotated[Optional[str], Header()] = None,
    session: Session = Depends(get_session),
) -> Optional[ApiKey]:
    """Verify API key and return the associated ApiKey model"""
    settings = get_settings()

    if not x_api_key:
        logger.warning("API key missing", extra={"endpoint": "sync-logs"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    # Check for development key
    if settings.debug and x_api_key == settings.default_api_key:
        return None  # Allow dev key without DB lookup

    # Find all active keys and check with bcrypt
    statement = select(ApiKey).where(
        ApiKey.is_active.is_(True)  # type: ignore[attr-defined]
    )
    api_keys = session.exec(statement).all()

    matched_key: Optional[ApiKey] = None
    for api_key in api_keys:
        # Check expiration
        if api_key.expires_at and api_key.expires_at < utc_now():
            continue
        if verify_api_key_hash(x_api_key, api_key.key_hash):
            matched_key = api_key
            break

    if not matched_key:
        logger.warning("Invalid or inactive API key", extra={"endpoint": "sync-logs"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    # Debounce last_used_at — only write if stale by 5+ minutes
    now = utc_now()
    if matched_key.last_used_at is None or now - matched_key.last_used_at > timedelta(
        minutes=5
    ):
        matched_key.last_used_at = now
        session.add(matched_key)
        session.commit()

    return matched_key


async def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
    authorization: Annotated[Optional[str], Header()] = None,
    access_token: Annotated[Optional[str], Cookie()] = None,
) -> User:
    """Extract and validate JWT from Authorization header or cookie.

    Checks Authorization header first (API clients), then falls back
    to access_token cookie (browser sessions).
    """
    token: Optional[str] = None

    # Try Authorization header first
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    # Fall back to cookie
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    try:
        payload = pyjwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = session.get(User, UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user


SessionDep = Annotated[Session, Depends(get_session)]
ApiKeyDep = Annotated[Optional[ApiKey], Depends(verify_api_key)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
