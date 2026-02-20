import hashlib
import logging
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Header, status
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models.sync_log import ApiKey

logger = logging.getLogger(__name__)


def hash_api_key(key: str) -> str:
    """Hash API key using SHA-256"""
    return hashlib.sha256(key.encode()).hexdigest()


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

    key_hash = hash_api_key(x_api_key)

    statement = select(ApiKey).where(
        ApiKey.key_hash == key_hash, ApiKey.is_active == True
    )
    api_key = session.exec(statement).first()

    if not api_key:
        logger.warning("Invalid or inactive API key", extra={"endpoint": "sync-logs"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    # Update last_used_at
    api_key.last_used_at = datetime.utcnow()
    session.add(api_key)
    session.commit()

    return api_key


SessionDep = Annotated[Session, Depends(get_session)]
ApiKeyDep = Annotated[Optional[ApiKey], Depends(verify_api_key)]
