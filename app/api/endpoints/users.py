"""Admin user management + user preferences endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import AdminDep, CurrentUserDep, SessionDep
from app.models.user import User
from app.schemas.user import (
    RoleUpdate,
    StatusUpdate,
    UserPreferencesUpdate,
    UserResponse,
)
from app.services.auth import (
    PASSWORD_RESET_TOKEN_EXPIRY,
    ROLE_ADMIN,
    VALID_ROLES,
    is_last_admin,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


# ---------------------------------------------------------------------------
# User preferences (any authenticated user)
# ---------------------------------------------------------------------------


@router.get("/me/preferences")
async def get_preferences(
    user: CurrentUserDep,
) -> dict:
    """Get the current user's preferences."""
    return user.preferences or {}


@router.patch("/me/preferences")
async def update_preferences(
    body: UserPreferencesUpdate,
    user: CurrentUserDep,
    session: SessionDep,
) -> dict:
    """Merge partial preferences into the current user's preferences."""
    current = dict(user.preferences or {})
    update_data = body.model_dump(exclude_none=True)
    current.update(update_data)
    user.preferences = current
    session.add(user)
    session.commit()
    session.refresh(user)
    return user.preferences or {}


@router.get("", response_model=list[UserResponse])
async def list_users(
    admin: AdminDep,
    session: SessionDep,
) -> list[User]:
    """List all users (admin only)."""
    statement = select(User).order_by(User.created_at.desc())
    return list(session.exec(statement).all())


@router.put("/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: UUID,
    body: RoleUpdate,
    admin: AdminDep,
    session: SessionDep,
) -> User:
    """Change a user's role (admin only)."""
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {body.role}. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        )

    # Cannot change own role
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # If demoting an admin, check at least one admin remains
    if target.role == ROLE_ADMIN and body.role != ROLE_ADMIN:
        if is_last_admin(session):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last admin",
            )

    target.role = body.role
    session.add(target)
    session.commit()
    session.refresh(target)
    logger.info(
        "Role changed: %s -> %s (by %s)", target.username, body.role, admin.username
    )
    return target


@router.put("/{user_id}/status", response_model=UserResponse)
async def change_user_status(
    user_id: UUID,
    body: StatusUpdate,
    admin: AdminDep,
    session: SessionDep,
) -> User:
    """Enable or disable a user account (admin only)."""
    # Cannot disable self
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own status",
        )

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    target.is_active = body.is_active
    session.add(target)
    session.commit()
    session.refresh(target)
    action = "enabled" if body.is_active else "disabled"
    logger.info("User %s: %s (by %s)", action, target.username, admin.username)
    return target


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    admin: AdminDep,
    session: SessionDep,
) -> None:
    """Delete a user (admin only)."""
    # Cannot delete self
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Cannot delete last admin
    if target.role == ROLE_ADMIN:
        if is_last_admin(session):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin",
            )

    session.delete(target)
    session.commit()
    logger.info("User deleted: %s (by %s)", target.username, admin.username)


@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: UUID,
    admin: AdminDep,
    session: SessionDep,
) -> dict:
    """Admin-initiated password reset for a user."""
    import secrets

    from app.models.user import PasswordResetToken
    from app.services.auth import hash_token
    from app.utils import utc_now

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    raw_token = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(
        user_id=target.id,
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + PASSWORD_RESET_TOKEN_EXPIRY,
    )
    session.add(reset_token)
    session.commit()

    logger.info(
        "Admin-initiated password reset for %s (by %s)",
        target.username,
        admin.username,
    )
    return {
        "message": f"Password reset token generated for {target.username}",
        "reset_token": raw_token,
    }
