"""API key management endpoints.

Covers: AC-011 (CRUD), AC-012 (role scoping)
"""

import logging
import secrets
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.api.deps import CurrentUserDep, SessionDep, hash_api_key
from app.models.sync_log import ApiKey
from app.schemas.user import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse
from app.services.auth import ROLE_ADMIN, role_at_least
from app.utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

KEY_PREFIX = "rsv_"


def _generate_raw_key() -> str:
    """Generate a cryptographically secure API key with prefix."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=ApiKeyCreatedResponse
)
async def create_api_key(
    body: ApiKeyCreate,
    user: CurrentUserDep,
    session: SessionDep,
):
    """Generate a new API key for the authenticated user."""
    # Validate role_override
    effective_role = user.role
    if body.role_override:
        if not role_at_least(user.role, body.role_override):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot create key with role '{body.role_override}' — exceeds your '{user.role}' role",
            )
        effective_role = body.role_override

    raw_key = _generate_raw_key()
    key_hash = hash_api_key(raw_key)

    api_key = ApiKey(
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        name=body.name,
        is_active=True,
        user_id=user.id,
        role_override=body.role_override,
        created_at=utc_now(),
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)

    logger.info("API key created", extra={"user": user.username, "key_name": body.name})

    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        role=effective_role,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: CurrentUserDep,
    session: SessionDep,
    all: Optional[bool] = Query(
        default=False, description="Admin: list all users' keys"
    ),
):
    """List API keys for the authenticated user (or all if admin with ?all=true)."""
    statement = select(ApiKey).where(
        ApiKey.is_active.is_(True)  # type: ignore[attr-defined]
    )

    if all and role_at_least(user.role, ROLE_ADMIN):
        # Admin sees all keys
        pass
    else:
        # Non-admin (or admin without ?all) sees only their own
        statement = statement.where(ApiKey.user_id == user.id)

    api_keys = session.exec(statement).all()
    return [ApiKeyResponse.model_validate(k) for k in api_keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    user: CurrentUserDep,
    session: SessionDep,
):
    """Revoke (deactivate) an API key. Users can revoke own keys; admins can revoke any."""
    api_key = session.get(ApiKey, key_id)
    if not api_key or not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Non-admin can only revoke their own keys
    if api_key.user_id != user.id and not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.is_active = False
    session.add(api_key)
    session.commit()

    logger.info("API key revoked", extra={"user": user.username, "key_id": str(key_id)})
