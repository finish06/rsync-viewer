"""Tests for password reset flow (AC-013).

Covers:
- Self-service: request reset, confirm with token, login with new password
- Token is single-use
- Token expires after 1 hour
- Invalid/missing token rejected
- Admin-initiated reset
- Non-existent email returns 200 (no information leakage)
"""

import os
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, select

from app.config import get_settings
from app.csrf import generate_csrf_token
from app.database import get_session
from app.main import app
from app.models.user import PasswordResetToken, User
from app.services.auth import (
    ROLE_ADMIN,
    ROLE_VIEWER,
    create_access_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.utils import utc_now

_TEST_SECRET = "test-secret-key"


def _setup_overrides(db_session: Session) -> None:
    os.environ["SECRET_KEY"] = _TEST_SECRET
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"
    get_settings.cache_clear()

    def get_test_session():
        yield db_session

    from tests.conftest import get_test_settings

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings


def _make_client(db_session: Session, user: User) -> AsyncClient:
    _setup_overrides(db_session)
    token = create_access_token(user.id, user.username, user.role)
    csrf_token = generate_csrf_token()
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf_token},
        cookies={"access_token": token, "csrf_token": csrf_token},
    )


def _make_unauth_client(db_session: Session) -> AsyncClient:
    _setup_overrides(db_session)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


def _create_user(
    db_session: Session,
    username: str,
    role: str = ROLE_VIEWER,
) -> User:
    user = User(
        username=username,
        email=f"{username}@test.com",
        password_hash=hash_password("OldPass1!"),
        role=role,
    )
    db_session.add(user)
    db_session.flush()
    return user


# --- Self-Service Password Reset ---


@pytest.mark.asyncio
async def test_ac013_request_reset_returns_200(db_session: Session) -> None:
    """POST /api/v1/auth/password-reset/request returns 200 for existing email."""
    _create_user(db_session, "user1")
    client = _make_unauth_client(db_session)

    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "user1@test.com"},
    )
    assert resp.status_code == 200
    assert "reset" in resp.json()["message"].lower()

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac013_request_reset_nonexistent_email_still_200(
    db_session: Session,
) -> None:
    """Non-existent email returns 200 (no information leakage)."""
    client = _make_unauth_client(db_session)

    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nobody@test.com"},
    )
    assert resp.status_code == 200

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac013_request_reset_creates_token(db_session: Session) -> None:
    """Requesting a reset creates a PasswordResetToken in the database."""
    user = _create_user(db_session, "user1")
    client = _make_unauth_client(db_session)

    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "user1@test.com"},
    )
    assert resp.status_code == 200

    # Token should exist in DB
    tokens = db_session.exec(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    ).all()
    assert len(tokens) >= 1

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac013_confirm_reset_changes_password(db_session: Session) -> None:
    """POST /api/v1/auth/password-reset/confirm changes password with valid token."""
    user = _create_user(db_session, "user1")
    client = _make_unauth_client(db_session)

    # Request reset
    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "user1@test.com"},
    )
    assert resp.status_code == 200

    # Extract token from response (console-logged mode exposes it in response)
    token_value = resp.json().get("reset_token")
    assert token_value is not None, (
        "Reset token should be returned in debug/console mode"
    )

    # Confirm reset
    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token_value, "new_password": "NewPass1!"},
    )
    assert resp.status_code == 200

    # Verify new password works
    db_session.refresh(user)
    assert verify_password("NewPass1!", user.password_hash)

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac013_token_single_use(db_session: Session) -> None:
    """Used token cannot be reused."""
    _create_user(db_session, "user1")
    client = _make_unauth_client(db_session)

    # Request + confirm
    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "user1@test.com"},
    )
    token_value = resp.json().get("reset_token")

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token_value, "new_password": "NewPass1!"},
    )
    assert resp.status_code == 200

    # Try to use the same token again
    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token_value, "new_password": "AnotherPass1!"},
    )
    assert resp.status_code == 400

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac013_expired_token_rejected(db_session: Session) -> None:
    """Expired token returns 400."""
    user = _create_user(db_session, "user1")

    # Manually create an expired token
    import secrets

    raw_token = secrets.token_urlsafe(32)
    expired_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utc_now() - timedelta(hours=2),
    )
    db_session.add(expired_token)
    db_session.flush()

    client = _make_unauth_client(db_session)
    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "NewPass1!"},
    )
    assert resp.status_code == 400

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac013_invalid_token_rejected(db_session: Session) -> None:
    """Invalid token returns 400."""
    client = _make_unauth_client(db_session)

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "completely-invalid-token", "new_password": "NewPass1!"},
    )
    assert resp.status_code == 400

    await client.aclose()
    app.dependency_overrides.clear()


# --- Admin-Initiated Reset ---


@pytest.mark.asyncio
async def test_ac013_admin_can_reset_user_password(db_session: Session) -> None:
    """Admin can trigger password reset for any user via POST /api/v1/users/{id}/reset-password."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    target = _create_user(db_session, "target1")
    client = _make_client(db_session, admin)

    resp = await client.post(f"/api/v1/users/{target.id}/reset-password")
    assert resp.status_code == 200
    # Should return the reset token (admin shares it with user)
    assert "reset_token" in resp.json()

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac013_non_admin_cannot_reset_others(db_session: Session) -> None:
    """Non-admin cannot trigger password reset for another user."""
    _create_user(db_session, "admin1", ROLE_ADMIN)
    operator = _create_user(db_session, "op1", "operator")
    target = _create_user(db_session, "target1")
    client = _make_client(db_session, operator)

    resp = await client.post(f"/api/v1/users/{target.id}/reset-password")
    assert resp.status_code == 403

    await client.aclose()
    app.dependency_overrides.clear()


# --- Password Reset UI ---


@pytest.mark.asyncio
async def test_ac013_forgot_password_page_accessible(db_session: Session) -> None:
    """GET /forgot-password page is accessible without auth."""
    client = _make_unauth_client(db_session)

    resp = await client.get("/forgot-password")
    assert resp.status_code == 200
    assert "email" in resp.text.lower() or "reset" in resp.text.lower()

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac013_reset_password_page_accessible(db_session: Session) -> None:
    """GET /reset-password page (with token param) is accessible without auth."""
    client = _make_unauth_client(db_session)

    resp = await client.get("/reset-password?token=some-token")
    assert resp.status_code == 200
    assert "password" in resp.text.lower()

    await client.aclose()
    app.dependency_overrides.clear()
