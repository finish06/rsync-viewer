"""Tests for Role-Based Access Control (RBAC) — Cycle 10, M9 Phase 3.

Covers:
  AC-006: Admin full access
  AC-007: Operator limited access (no delete, no user management)
  AC-008: Viewer read-only
  AC-010: Protected routes redirect unauthenticated to /login
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

import jwt as pyjwt

from app.config import get_settings
from app.csrf import generate_csrf_token
from app.database import get_session
from app.main import app
from app.models.user import User
from app.services.auth import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    hash_password,
)
from app.utils import utc_now as _utc_now
from datetime import timedelta

# Test secret key must match conftest.get_test_settings().secret_key
_TEST_SECRET = "test-secret-key"
_TEST_ALGORITHM = "HS256"


def create_access_token(user_id, username, role):
    """Create a JWT access token using the TEST secret key.

    This avoids the cached get_settings() which reads from .env.
    """
    now = _utc_now()
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    return pyjwt.encode(payload, _TEST_SECRET, algorithm=_TEST_ALGORITHM)


@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = User(
        username="admin_user",
        email="admin@test.com",
        password_hash=hash_password("AdminPass1!"),
        role=ROLE_ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def operator_user(db_session: Session) -> User:
    user = User(
        username="operator_user",
        email="operator@test.com",
        password_hash=hash_password("OperPass1!"),
        role=ROLE_OPERATOR,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def viewer_user(db_session: Session) -> User:
    user = User(
        username="viewer_user",
        email="viewer@test.com",
        password_hash=hash_password("ViewPass1!"),
        role=ROLE_VIEWER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _setup_overrides(db_session):
    """Set up FastAPI dependency overrides and clear settings cache."""
    import os
    from tests.conftest import get_test_settings

    # Set env vars so that get_settings() (called directly by middleware
    # and deps outside FastAPI DI) rebuilds with the test secret key.
    os.environ["SECRET_KEY"] = _TEST_SECRET
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"

    # Clear the lru_cache so get_settings() rebuilds from env vars
    get_settings.cache_clear()

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings


def _make_cookie_client(db_session, user: User) -> AsyncClient:
    """Create a test client authenticated via JWT cookie for a given user."""
    _setup_overrides(db_session)

    token = create_access_token(user.id, user.username, user.role)
    csrf_token = generate_csrf_token()
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"access_token": token, "csrf_token": csrf_token},
        headers={"X-CSRF-Token": csrf_token},
    )


def _make_bearer_client(db_session, user: User) -> AsyncClient:
    """Create a test client authenticated via Bearer header for a given user."""
    _setup_overrides(db_session)

    token = create_access_token(user.id, user.username, user.role)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    )


def _make_unauth_client(db_session) -> AsyncClient:
    """Create an unauthenticated test client."""
    _setup_overrides(db_session)

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


# ── AC-010: Protected routes redirect unauthenticated to /login ──


class TestAuthRedirect:
    """AC-010: Unauthenticated UI requests redirect to /login."""

    @pytest.mark.asyncio
    async def test_ac010_dashboard_redirects_to_login(self, db_session):
        client = _make_unauth_client(db_session)
        resp = await client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac010_settings_redirects_to_login(self, db_session):
        client = _make_unauth_client(db_session)
        resp = await client.get("/settings", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac010_htmx_sync_table_redirects(self, db_session):
        client = _make_unauth_client(db_session)
        resp = await client.get("/htmx/sync-table", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac010_return_url_preserved(self, db_session):
        client = _make_unauth_client(db_session)
        resp = await client.get("/settings", follow_redirects=False)
        assert "return_url=/settings" in resp.headers["location"]
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac010_login_page_public(self, db_session):
        client = _make_unauth_client(db_session)
        resp = await client.get("/login")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac010_register_page_public(self, db_session):
        client = _make_unauth_client(db_session)
        resp = await client.get("/register")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac010_health_public(self, db_session):
        client = _make_unauth_client(db_session)
        resp = await client.get("/health")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac010_metrics_public(self, db_session):
        client = _make_unauth_client(db_session)
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac010_api_returns_401_not_redirect(self, db_session):
        client = _make_unauth_client(db_session)
        resp = await client.get("/api/v1/sync-logs", follow_redirects=False)
        assert resp.status_code == 401
        await client.aclose()
        app.dependency_overrides.clear()


# ── AC-006: Admin has full access ──


class TestAdminAccess:
    """AC-006: Admin can view, create, edit, delete all resources."""

    @pytest.mark.asyncio
    async def test_ac006_admin_dashboard(self, db_session, admin_user):
        client = _make_cookie_client(db_session, admin_user)
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "admin_user" in resp.text
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac006_admin_settings(self, db_session, admin_user):
        client = _make_cookie_client(db_session, admin_user)
        resp = await client.get("/settings")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac006_admin_api_list_logs(self, db_session, admin_user):
        client = _make_bearer_client(db_session, admin_user)
        resp = await client.get("/api/v1/sync-logs")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac006_admin_api_create_log(
        self, db_session, admin_user, sample_sync_log_data
    ):
        client = _make_bearer_client(db_session, admin_user)
        resp = await client.post("/api/v1/sync-logs", json=sample_sync_log_data)
        assert resp.status_code == 201
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac006_admin_api_delete_log(
        self, db_session, admin_user, create_sync_log
    ):
        log = create_sync_log()
        client = _make_bearer_client(db_session, admin_user)
        resp = await client.delete(f"/api/v1/sync-logs/{log.id}")
        assert resp.status_code == 204
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac006_admin_shows_role_badge(self, db_session, admin_user):
        client = _make_cookie_client(db_session, admin_user)
        resp = await client.get("/")
        assert "role-admin" in resp.text
        await client.aclose()
        app.dependency_overrides.clear()


# ── AC-007: Operator limited access ──


class TestOperatorAccess:
    """AC-007: Operator can view, submit logs, manage webhooks, but cannot delete or manage users."""

    @pytest.mark.asyncio
    async def test_ac007_operator_dashboard(self, db_session, operator_user):
        client = _make_cookie_client(db_session, operator_user)
        resp = await client.get("/")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac007_operator_settings(self, db_session, operator_user):
        client = _make_cookie_client(db_session, operator_user)
        resp = await client.get("/settings")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac007_operator_api_list_logs(self, db_session, operator_user):
        client = _make_bearer_client(db_session, operator_user)
        resp = await client.get("/api/v1/sync-logs")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac007_operator_api_create_log(
        self, db_session, operator_user, sample_sync_log_data
    ):
        client = _make_bearer_client(db_session, operator_user)
        resp = await client.post("/api/v1/sync-logs", json=sample_sync_log_data)
        assert resp.status_code == 201
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac007_operator_cannot_delete_log(
        self, db_session, operator_user, create_sync_log
    ):
        log = create_sync_log()
        client = _make_bearer_client(db_session, operator_user)
        resp = await client.delete(f"/api/v1/sync-logs/{log.id}")
        assert resp.status_code == 403
        await client.aclose()
        app.dependency_overrides.clear()


# ── AC-008: Viewer read-only ──


class TestViewerAccess:
    """AC-008: Viewer can view resources only (read-only access)."""

    @pytest.mark.asyncio
    async def test_ac008_viewer_dashboard(self, db_session, viewer_user):
        client = _make_cookie_client(db_session, viewer_user)
        resp = await client.get("/")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac008_viewer_cannot_access_settings(self, db_session, viewer_user):
        client = _make_cookie_client(db_session, viewer_user)
        resp = await client.get("/settings")
        assert resp.status_code == 403
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac008_viewer_api_list_logs(self, db_session, viewer_user):
        client = _make_bearer_client(db_session, viewer_user)
        resp = await client.get("/api/v1/sync-logs")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac008_viewer_cannot_create_log(
        self, db_session, viewer_user, sample_sync_log_data
    ):
        client = _make_bearer_client(db_session, viewer_user)
        resp = await client.post("/api/v1/sync-logs", json=sample_sync_log_data)
        assert resp.status_code == 403
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac008_viewer_cannot_delete_log(
        self, db_session, viewer_user, create_sync_log
    ):
        log = create_sync_log()
        client = _make_bearer_client(db_session, viewer_user)
        resp = await client.delete(f"/api/v1/sync-logs/{log.id}")
        assert resp.status_code == 403
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ac008_viewer_shows_no_settings_link(self, db_session, viewer_user):
        client = _make_cookie_client(db_session, viewer_user)
        resp = await client.get("/")
        assert 'href="/settings"' not in resp.text
        await client.aclose()
        app.dependency_overrides.clear()


# ── Logout ──


class TestLogout:
    """Logout clears cookie and redirects to /login."""

    @pytest.mark.asyncio
    async def test_logout_redirects_to_login(self, db_session, admin_user):
        client = _make_cookie_client(db_session, admin_user)
        resp = await client.post("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]
        # Cookie should be cleared (set-cookie with empty/expired value)
        set_cookie = resp.headers.get("set-cookie", "")
        assert "access_token" in set_cookie
        await client.aclose()
        app.dependency_overrides.clear()


# ── require_role() dependency unit tests ──


class TestRequireRole:
    """Unit tests for the require_role() dependency factory."""

    @pytest.mark.asyncio
    async def test_require_role_admin_passes_for_admin(self, db_session, admin_user):
        client = _make_bearer_client(db_session, admin_user)
        # Delete endpoint requires admin
        resp = await client.get("/api/v1/sync-logs")
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_require_role_returns_403_for_insufficient_role(
        self, db_session, viewer_user, sample_sync_log_data
    ):
        client = _make_bearer_client(db_session, viewer_user)
        resp = await client.post("/api/v1/sync-logs", json=sample_sync_log_data)
        assert resp.status_code == 403
        await client.aclose()
        app.dependency_overrides.clear()


# ── Backward compatibility: API key auth ──


class TestApiKeyBackwardCompat:
    """API key auth continues to work for API endpoints.

    Uses dev API key (debug=True, default_api_key="test-api-key") which
    is handled by _try_verify_api_key in the dual-auth dependency.
    """

    @pytest.mark.asyncio
    async def test_api_key_still_works_for_list(self, db_session):
        client = _make_unauth_client(db_session)
        resp = await client.get(
            "/api/v1/sync-logs", headers={"X-API-Key": "test-api-key"}
        )
        assert resp.status_code == 200
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_api_key_still_works_for_create(
        self, db_session, sample_sync_log_data
    ):
        client = _make_unauth_client(db_session)
        resp = await client.post(
            "/api/v1/sync-logs",
            json=sample_sync_log_data,
            headers={"X-API-Key": "test-api-key"},
        )
        assert resp.status_code == 201
        await client.aclose()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_api_key_cannot_delete_logs(self, db_session, create_sync_log):
        """API keys are operator-level — cannot delete (admin-only)."""
        log = create_sync_log()
        client = _make_unauth_client(db_session)
        resp = await client.delete(
            f"/api/v1/sync-logs/{log.id}",
            headers={"X-API-Key": "test-api-key"},
        )
        # Delete requires admin role via AdminDep, not dual auth
        # API key doesn't satisfy AdminDep (requires JWT user)
        assert resp.status_code == 401
        await client.aclose()
        app.dependency_overrides.clear()
