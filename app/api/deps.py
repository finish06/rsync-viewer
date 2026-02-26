import logging
from datetime import timedelta
from typing import Annotated, Callable, Optional
from uuid import UUID

import bcrypt
import jwt as pyjwt
from fastapi import Cookie, Depends, HTTPException, Header, Request, status
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.database import get_session
from app.models.sync_log import ApiKey
from app.models.user import User
from app.services.auth import ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER, role_at_least
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


async def get_optional_user(
    request: Request,
    session: Session = Depends(get_session),
    authorization: Annotated[Optional[str], Header()] = None,
    access_token: Annotated[Optional[str], Cookie()] = None,
) -> Optional[User]:
    """Extract user from JWT if present, return None if not authenticated.

    Used for UI routes where we need user context but the middleware
    handles the redirect for unauthenticated users.
    """
    token: Optional[str] = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif access_token:
        token = access_token

    if not token:
        return None

    settings = get_settings()
    try:
        payload = pyjwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None

    if payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = session.get(User, UUID(user_id))
    if not user or not user.is_active:
        return None

    return user


def require_role(minimum_role: str) -> Callable:
    """FastAPI dependency factory that enforces a minimum role.

    Usage:
        AdminDep = Annotated[User, Depends(require_role(ROLE_ADMIN))]
    """

    async def _check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not role_at_least(user.role, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role} role",
            )
        return user

    return _check


async def _try_verify_api_key(
    x_api_key: str,
    session: Session,
    settings: "Settings",
) -> Optional[ApiKey]:
    """Try to verify API key. Raises HTTPException on invalid key."""
    if not x_api_key:
        return None
    # Check for development key
    if settings.debug and x_api_key == settings.default_api_key:
        return None  # Valid dev key — returns None (no ApiKey model)

    statement = select(ApiKey).where(
        ApiKey.is_active.is_(True)  # type: ignore[attr-defined]
    )
    api_keys = session.exec(statement).all()

    matched_key: Optional[ApiKey] = None
    for api_key in api_keys:
        if api_key.expires_at and api_key.expires_at < utc_now():
            continue
        if verify_api_key_hash(x_api_key, api_key.key_hash):
            matched_key = api_key
            break

    if not matched_key and not (settings.debug and x_api_key == settings.default_api_key):
        logger.warning("Invalid or inactive API key", extra={"endpoint": "dual-auth"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    if matched_key:
        now = utc_now()
        if matched_key.last_used_at is None or now - matched_key.last_used_at > timedelta(
            minutes=5
        ):
            matched_key.last_used_at = now
            session.add(matched_key)
            session.commit()

    return matched_key


# Sentinel to distinguish "no API key header" from "invalid API key"
_API_KEY_NOT_PROVIDED = object()


async def verify_api_key_or_jwt(
    request: Request,
    session: Session = Depends(get_session),
    settings: "Settings" = Depends(get_settings),
    x_api_key: Annotated[Optional[str], Header()] = None,
    authorization: Annotated[Optional[str], Header()] = None,
    access_token: Annotated[Optional[str], Cookie()] = None,
) -> tuple[Optional[User], Optional[ApiKey]]:
    """Authenticate via API key OR JWT. Returns (user, api_key).

    Priority:
    - If X-API-Key header is present, authenticate via API key → (None, api_key)
    - If Bearer header is present, authenticate via JWT → (user, None)
    - If access_token cookie is present, authenticate via JWT → (user, None)
    - If none, raises 401
    """
    # Try explicit API key first (explicit header takes priority)
    if x_api_key:
        api_key_obj = await _try_verify_api_key(
            x_api_key=x_api_key, session=session, settings=settings
        )
        return (None, api_key_obj)

    # Try JWT (Bearer header or cookie)
    jwt_token: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization[7:]
    elif access_token:
        jwt_token = access_token

    if jwt_token:
        try:
            payload = pyjwt.decode(
                jwt_token,
                settings.secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
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
        return (user, None)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role_or_api_key(minimum_role: str) -> Callable:
    """Dependency factory for endpoints accepting API key OR JWT with role check.

    API keys are treated as operator-level access.
    """

    async def _check(
        auth: Annotated[
            tuple[Optional[User], Optional[ApiKey]],
            Depends(verify_api_key_or_jwt),
        ],
    ) -> tuple[Optional[User], Optional[ApiKey]]:
        user, api_key = auth
        if user:
            if not role_at_least(user.role, minimum_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires {minimum_role} role",
                )
        elif api_key is not None or api_key is None:
            # API key auth — treated as operator level
            if not role_at_least(ROLE_OPERATOR, minimum_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key access is operator-level; requires {minimum_role}",
                )
        return auth

    return _check


SessionDep = Annotated[Session, Depends(get_session)]
ApiKeyDep = Annotated[Optional[ApiKey], Depends(verify_api_key)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
OptionalUserDep = Annotated[Optional[User], Depends(get_optional_user)]
AdminDep = Annotated[User, Depends(require_role(ROLE_ADMIN))]
OperatorDep = Annotated[User, Depends(require_role(ROLE_OPERATOR))]
ViewerDep = Annotated[User, Depends(require_role(ROLE_VIEWER))]
