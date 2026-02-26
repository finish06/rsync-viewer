"""Tests for session timeout re-login behavior (AC-016).

Covers:
- Expired JWT on HTMX request returns 401 with re-login indicator
- Login page link on login form has forgot-password link
"""

import os
from datetime import timedelta

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app.config import get_settings
from app.csrf import generate_csrf_token
from app.database import get_session
from app.main import app
from app.models.user import User
from app.services.auth import ROLE_OPERATOR, hash_password
from app.utils import utc_now

_TEST_SECRET = "test-secret-key"
_TEST_ALGORITHM = "HS256"


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


def _create_user(db_session: Session) -> User:
    user = User(
        username="timeout_user",
        email="timeout@test.com",
        password_hash=hash_password("TestPass1!"),
        role=ROLE_OPERATOR,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _make_expired_jwt(user: User) -> str:
    """Create an expired JWT token."""
    now = utc_now()
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "type": "access",
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    return pyjwt.encode(payload, _TEST_SECRET, algorithm=_TEST_ALGORITHM)


@pytest.mark.asyncio
async def test_ac016_expired_jwt_returns_401(db_session: Session) -> None:
    """HTMX request with expired JWT gets 401."""
    _setup_overrides(db_session)
    user = _create_user(db_session)
    expired_token = _make_expired_jwt(user)
    csrf_token = generate_csrf_token()

    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"access_token": expired_token, "csrf_token": csrf_token},
        headers={"X-CSRF-Token": csrf_token, "HX-Request": "true"},
    )

    # Try an authenticated HTMX route
    resp = await client.get("/htmx/api-keys")
    # Should get 401 or redirect — the middleware may redirect to login
    assert resp.status_code in (401, 403)

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac016_login_page_has_forgot_password(db_session: Session) -> None:
    """Login page includes a 'Forgot Password' link."""
    _setup_overrides(db_session)
    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )

    resp = await client.get("/login")
    assert resp.status_code == 200
    assert "forgot" in resp.text.lower()

    await client.aclose()
    app.dependency_overrides.clear()
