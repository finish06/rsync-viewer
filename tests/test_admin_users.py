"""Tests for admin user management (AC-006).

Covers:
- Admin can list all users
- Admin can change user roles
- Admin can enable/disable users
- Admin can delete users
- Safety: cannot demote/delete self
- Safety: at least one admin must exist
- Non-admin gets 403
- Unauthenticated gets 401
"""

import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app.config import get_settings
from app.csrf import generate_csrf_token
from app.database import get_session
from app.main import app
from app.models.user import User
from app.services.auth import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    create_access_token,
    hash_password,
)

_TEST_SECRET = "test-secret-key"


def _setup_overrides(db_session: Session) -> None:
    """Configure test environment."""
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
    """Create an authenticated test client for the given user."""
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
    """Create an unauthenticated test client."""
    _setup_overrides(db_session)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


def _create_user(
    db_session: Session,
    username: str,
    role: str = ROLE_VIEWER,
    is_active: bool = True,
) -> User:
    """Create a user in the test database."""
    user = User(
        username=username,
        email=f"{username}@test.com",
        password_hash=hash_password("TestPass1!"),
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.flush()
    return user


# --- Admin List Users ---


@pytest.mark.asyncio
async def test_ac006_admin_can_list_users(db_session: Session) -> None:
    """Admin can list all users via GET /api/v1/users."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    _create_user(db_session, "user1", ROLE_OPERATOR)
    _create_user(db_session, "user2", ROLE_VIEWER)
    client = _make_client(db_session, admin)

    resp = await client.get("/api/v1/users")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    usernames = [u["username"] for u in data]
    assert "admin1" in usernames
    assert "user1" in usernames
    assert "user2" in usernames

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_operator_cannot_list_users(db_session: Session) -> None:
    """Operator gets 403 on GET /api/v1/users."""
    _create_user(db_session, "admin1", ROLE_ADMIN)
    operator = _create_user(db_session, "op1", ROLE_OPERATOR)
    client = _make_client(db_session, operator)

    resp = await client.get("/api/v1/users")
    assert resp.status_code == 403

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_viewer_cannot_list_users(db_session: Session) -> None:
    """Viewer gets 403 on GET /api/v1/users."""
    _create_user(db_session, "admin1", ROLE_ADMIN)
    viewer = _create_user(db_session, "viewer1", ROLE_VIEWER)
    client = _make_client(db_session, viewer)

    resp = await client.get("/api/v1/users")
    assert resp.status_code == 403

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_unauthenticated_cannot_list_users(db_session: Session) -> None:
    """Unauthenticated request gets 401 on GET /api/v1/users."""
    client = _make_unauth_client(db_session)

    resp = await client.get("/api/v1/users")
    assert resp.status_code == 401

    await client.aclose()
    app.dependency_overrides.clear()


# --- Admin Change Role ---


@pytest.mark.asyncio
async def test_ac006_admin_can_change_user_role(db_session: Session) -> None:
    """Admin can change a user's role via PUT /api/v1/users/{id}/role."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    target = _create_user(db_session, "target1", ROLE_VIEWER)
    client = _make_client(db_session, admin)

    resp = await client.put(
        f"/api/v1/users/{target.id}/role",
        json={"role": ROLE_OPERATOR},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == ROLE_OPERATOR

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_admin_cannot_change_own_role(db_session: Session) -> None:
    """Admin cannot demote themselves."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    client = _make_client(db_session, admin)

    resp = await client.put(
        f"/api/v1/users/{admin.id}/role",
        json={"role": ROLE_VIEWER},
    )
    assert resp.status_code == 400

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_cannot_remove_last_admin(db_session: Session) -> None:
    """Cannot change role of the last admin (must always have at least one)."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    target = _create_user(db_session, "admin2", ROLE_ADMIN)
    client = _make_client(db_session, admin)

    # Demote admin2 — should succeed (admin1 still exists)
    resp = await client.put(
        f"/api/v1/users/{target.id}/role",
        json={"role": ROLE_OPERATOR},
    )
    assert resp.status_code == 200

    # Now try to demote admin1 (the last admin) — should fail
    resp = await client.put(
        f"/api/v1/users/{admin.id}/role",
        json={"role": ROLE_OPERATOR},
    )
    assert resp.status_code == 400

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_invalid_role_rejected(db_session: Session) -> None:
    """Invalid role value returns 422 or 400."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    target = _create_user(db_session, "target1", ROLE_VIEWER)
    client = _make_client(db_session, admin)

    resp = await client.put(
        f"/api/v1/users/{target.id}/role",
        json={"role": "superuser"},
    )
    assert resp.status_code in (400, 422)

    await client.aclose()
    app.dependency_overrides.clear()


# --- Admin Enable/Disable Users ---


@pytest.mark.asyncio
async def test_ac006_admin_can_disable_user(db_session: Session) -> None:
    """Admin can disable a user via PUT /api/v1/users/{id}/status."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    target = _create_user(db_session, "target1", ROLE_VIEWER)
    client = _make_client(db_session, admin)

    resp = await client.put(
        f"/api/v1/users/{target.id}/status",
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_admin_can_enable_user(db_session: Session) -> None:
    """Admin can re-enable a disabled user."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    target = _create_user(db_session, "target1", ROLE_VIEWER, is_active=False)
    client = _make_client(db_session, admin)

    resp = await client.put(
        f"/api/v1/users/{target.id}/status",
        json={"is_active": True},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_admin_cannot_disable_self(db_session: Session) -> None:
    """Admin cannot disable their own account."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    client = _make_client(db_session, admin)

    resp = await client.put(
        f"/api/v1/users/{admin.id}/status",
        json={"is_active": False},
    )
    assert resp.status_code == 400

    await client.aclose()
    app.dependency_overrides.clear()


# --- Admin Delete User ---


@pytest.mark.asyncio
async def test_ac006_admin_can_delete_user(db_session: Session) -> None:
    """Admin can delete a user via DELETE /api/v1/users/{id}."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    target = _create_user(db_session, "target1", ROLE_VIEWER)
    client = _make_client(db_session, admin)

    resp = await client.delete(f"/api/v1/users/{target.id}")
    assert resp.status_code == 204

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_admin_cannot_delete_self(db_session: Session) -> None:
    """Admin cannot delete their own account."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    client = _make_client(db_session, admin)

    resp = await client.delete(f"/api/v1/users/{admin.id}")
    assert resp.status_code == 400

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_cannot_delete_last_admin(db_session: Session) -> None:
    """Cannot delete the last admin user."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    admin2 = _create_user(db_session, "admin2", ROLE_ADMIN)
    client = _make_client(db_session, admin)

    # Delete admin2 — should succeed
    resp = await client.delete(f"/api/v1/users/{admin2.id}")
    assert resp.status_code == 204

    # Cannot delete self (last admin)
    resp = await client.delete(f"/api/v1/users/{admin.id}")
    assert resp.status_code == 400

    await client.aclose()
    app.dependency_overrides.clear()


# --- Admin UI Page ---


@pytest.mark.asyncio
async def test_ac006_admin_can_access_admin_page(db_session: Session) -> None:
    """Admin can access /admin/users page."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    client = _make_client(db_session, admin)

    resp = await client.get("/admin/users")
    assert resp.status_code == 200
    assert "admin1" in resp.text

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_non_admin_cannot_access_admin_page(db_session: Session) -> None:
    """Non-admin gets 403 on /admin/users page."""
    _create_user(db_session, "admin1", ROLE_ADMIN)
    operator = _create_user(db_session, "op1", ROLE_OPERATOR)
    client = _make_client(db_session, operator)

    resp = await client.get("/admin/users")
    assert resp.status_code == 403

    await client.aclose()
    app.dependency_overrides.clear()


# --- HTMX Admin Routes ---


@pytest.mark.asyncio
async def test_ac006_htmx_user_list(db_session: Session) -> None:
    """HTMX route returns user list partial."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    _create_user(db_session, "user1", ROLE_VIEWER)
    client = _make_client(db_session, admin)

    resp = await client.get("/htmx/admin/users")
    assert resp.status_code == 200
    assert "user1" in resp.text

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_htmx_change_role(db_session: Session) -> None:
    """HTMX route changes user role and returns updated list."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    target = _create_user(db_session, "target1", ROLE_VIEWER)
    client = _make_client(db_session, admin)

    resp = await client.put(
        f"/htmx/admin/users/{target.id}/role",
        data={"role": ROLE_OPERATOR},
    )
    assert resp.status_code == 200

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_htmx_toggle_status(db_session: Session) -> None:
    """HTMX route toggles user active status."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    target = _create_user(db_session, "target1", ROLE_VIEWER)
    client = _make_client(db_session, admin)

    resp = await client.put(f"/htmx/admin/users/{target.id}/toggle-status")
    assert resp.status_code == 200

    await client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac006_htmx_delete_user(db_session: Session) -> None:
    """HTMX route deletes user and returns updated list."""
    admin = _create_user(db_session, "admin1", ROLE_ADMIN)
    target = _create_user(db_session, "target1", ROLE_VIEWER)
    client = _make_client(db_session, admin)

    resp = await client.delete(f"/htmx/admin/users/{target.id}")
    assert resp.status_code == 200
    assert "target1" not in resp.text

    await client.aclose()
    app.dependency_overrides.clear()
