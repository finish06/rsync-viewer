import logging
import secrets
from datetime import timedelta
from uuid import UUID

import jwt as pyjwt
from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import SessionDep
from app.config import get_settings
from app.models.user import PasswordResetToken, RefreshToken, User
from app.schemas.user import (
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
    verify_token,
)
from app.services.registration import RegistrationError, register_user
from app.utils import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(user_data: UserCreate, session: SessionDep) -> User:
    """Register a new user. First registered user gets Admin role."""
    settings = get_settings()
    if not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is currently disabled",
        )

    try:
        return register_user(
            session,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
        )
    except RegistrationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT tokens",
)
async def login(credentials: UserLogin, session: SessionDep) -> TokenResponse:
    """Authenticate with username and password, receive access and refresh tokens."""
    user = session.exec(
        select(User).where(User.username == credentials.username)
    ).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Generate tokens
    access_token = create_access_token(user.id, user.username, user.role)
    refresh_token_str = create_refresh_token(user.id)

    # Store hashed refresh token in database
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token_str),
        expires_at=utc_now() + timedelta(days=get_settings().jwt_refresh_expiry_days),
    )
    session.add(refresh_token_record)

    # Update last login
    user.last_login_at = utc_now()
    session.add(user)
    session.commit()

    settings = get_settings()
    logger.info(
        "User logged in",
        extra={"user_id": str(user.id), "username": user.username},
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        token_type="bearer",
        expires_in=settings.jwt_access_expiry_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an expired access token",
)
async def refresh(body: RefreshTokenRequest, session: SessionDep) -> TokenResponse:
    """Use a valid refresh token to get a new access token."""
    try:
        payload = decode_token(body.refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )
    except pyjwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Verify user still exists and is active
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

    # Verify refresh token exists in database and is not revoked
    stored_tokens = session.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked.is_(False),  # type: ignore[attr-defined]
        )
    ).all()

    token_valid = False
    for stored_token in stored_tokens:
        if verify_token(body.refresh_token, stored_token.token_hash):
            # Revoke the used refresh token (rotation)
            stored_token.revoked = True
            session.add(stored_token)
            token_valid = True
            break

    if not token_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or already revoked",
        )

    # Issue new tokens
    new_access_token = create_access_token(user.id, user.username, user.role)
    new_refresh_token = create_refresh_token(user.id)

    # Store new refresh token
    settings = get_settings()
    new_refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh_token),
        expires_at=utc_now() + timedelta(days=settings.jwt_refresh_expiry_days),
    )
    session.add(new_refresh_record)
    session.commit()

    logger.info(
        "Token refreshed",
        extra={"user_id": str(user.id), "username": user.username},
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_expiry_minutes * 60,
    )


@router.post(
    "/password-reset/request",
    response_model=PasswordResetResponse,
    summary="Request a password reset",
)
async def request_password_reset(
    body: PasswordResetRequest, session: SessionDep
) -> PasswordResetResponse:
    """Request a password reset. Token is logged to console (no SMTP in MVP).

    Always returns 200 regardless of whether email exists (no info leakage).
    """
    user = session.exec(select(User).where(User.email == body.email)).first()

    if not user:
        # Don't reveal whether email exists
        return PasswordResetResponse(
            message="If an account with that email exists, a reset link has been sent."
        )

    # OIDC users cannot reset local passwords
    if user.auth_provider == "oidc":
        return PasswordResetResponse(
            message="This account uses SSO. Please log in with your identity provider."
        )

    # Generate reset token
    raw_token = secrets.token_urlsafe(32)
    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + timedelta(hours=1),
    )
    session.add(reset_record)
    session.commit()

    settings = get_settings()

    # In debug/console mode, log the token so admins can manually reset
    if settings.debug:
        logger.info(
            "PASSWORD RESET TOKEN for %s: %s",
            user.username,
            raw_token,
        )

    return PasswordResetResponse(
        message="If an account with that email exists, a reset link has been sent.",
        reset_token=raw_token if settings.debug else None,
    )


@router.post(
    "/password-reset/confirm",
    summary="Reset password with token",
)
async def confirm_password_reset(
    body: PasswordResetConfirm, session: SessionDep
) -> dict:
    """Reset password using a valid, unused, non-expired token."""
    # Find all unused, non-expired tokens
    now = utc_now()
    tokens = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.used.is_(False),  # type: ignore[attr-defined]
            PasswordResetToken.expires_at > now,
        )
    ).all()

    matched_token = None
    for token_record in tokens:
        if verify_token(body.token, token_record.token_hash):
            matched_token = token_record
            break

    if not matched_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already used reset token",
        )

    # Load user and update password
    user = session.get(User, matched_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    user.password_hash = hash_password(body.new_password)
    user.updated_at = now
    session.add(user)

    # Mark token as used
    matched_token.used = True
    session.add(matched_token)
    session.commit()

    logger.info("Password reset completed for %s", user.username)
    return {"message": "Password has been reset successfully."}
