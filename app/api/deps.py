import logging
from datetime import timedelta
from typing import Annotated, Optional

import bcrypt
from fastapi import Depends, HTTPException, Header, status
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models.sync_log import ApiKey
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


SessionDep = Annotated[Session, Depends(get_session)]
ApiKeyDep = Annotated[Optional[ApiKey], Depends(verify_api_key)]
