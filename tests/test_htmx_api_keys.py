"""Tests for HTMX API key management routes (app/routes/api_keys.py)."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import hash_api_key
from app.csrf import generate_csrf_token
from app.main import app
from app.models.sync_log import ApiKey as ApiKeyModel
from app.models.user import User
from app.services.auth import ROLE_OPERATOR, ROLE_VIEWER, hash_password
from app.utils import utc_now
from tests.conftest import _make_test_jwt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_api_key(db_session, user_id, name="test-key", is_active=True):
    """Insert an API key directly and return the model instance."""
    key = ApiKeyModel(
        key_hash=hash_api_key(f"rsv_fake_{name}"),
        key_prefix="rsv_fake",
        name=name,
        is_active=is_active,
        user_id=user_id,
        created_at=utc_now(),
    )
    db_session.add(key)
    db_session.flush()
    return key


def _get_test_user(db_session) -> User:
    """Retrieve the test-operator user created by the client fixture."""
    from sqlmodel import select

    user = db_session.exec(select(User).where(User.username == "test-operator")).first()
    assert user is not None
    return user


# ---------------------------------------------------------------------------
# GET /htmx/api-keys — list
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_api_keys_authenticated(client, db_session):
    """Authenticated user sees their active API keys."""
    user = _get_test_user(db_session)
    _create_api_key(db_session, user.id, name="my-key-1")
    _create_api_key(db_session, user.id, name="my-key-2")

    resp = await client.get("/htmx/api-keys")
    assert resp.status_code == 200
    assert "my-key-1" in resp.text
    assert "my-key-2" in resp.text


@pytest.mark.anyio
async def test_list_api_keys_excludes_inactive(client, db_session):
    """Inactive keys are not shown in the list."""
    user = _get_test_user(db_session)
    _create_api_key(db_session, user.id, name="active-key")
    _create_api_key(db_session, user.id, name="revoked-key", is_active=False)

    resp = await client.get("/htmx/api-keys")
    assert resp.status_code == 200
    assert "active-key" in resp.text
    assert "revoked-key" not in resp.text


@pytest.mark.anyio
async def test_list_api_keys_unauthenticated(unauth_client):
    """Unauthenticated GET is redirected to /login by AuthRedirectMiddleware."""
    resp = await unauth_client.get("/htmx/api-keys", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("location", "")


# ---------------------------------------------------------------------------
# GET /htmx/api-keys/add — form
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_add_form_authenticated(client):
    """Authenticated user gets the creation form partial."""
    resp = await client.get("/htmx/api-keys/add")
    assert resp.status_code == 200
    # The form partial should contain form elements
    assert "form" in resp.text.lower() or "name" in resp.text.lower()


@pytest.mark.anyio
async def test_add_form_unauthenticated(unauth_client):
    """Unauthenticated GET is redirected to /login."""
    resp = await unauth_client.get("/htmx/api-keys/add", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("location", "")


# ---------------------------------------------------------------------------
# POST /htmx/api-keys — create
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_api_key_valid(client, db_session):
    """Creating a key with a valid name returns the raw key."""
    resp = await client.post(
        "/htmx/api-keys",
        data={"name": "production-key"},
    )
    assert resp.status_code == 200
    assert "rsv_" in resp.text  # Raw key is displayed once


@pytest.mark.anyio
async def test_create_api_key_empty_name(client):
    """Empty name returns form with error message."""
    resp = await client.post(
        "/htmx/api-keys",
        data={"name": ""},
    )
    assert resp.status_code == 200
    assert "Name is required" in resp.text


@pytest.mark.anyio
async def test_create_api_key_whitespace_name(client):
    """Whitespace-only name is treated as empty."""
    resp = await client.post(
        "/htmx/api-keys",
        data={"name": "   "},
    )
    assert resp.status_code == 200
    assert "Name is required" in resp.text


@pytest.mark.anyio
async def test_create_api_key_role_override_same_level(client, db_session):
    """Operator can create a key with operator-level role override."""
    resp = await client.post(
        "/htmx/api-keys",
        data={"name": "same-role-key", "role_override": ROLE_OPERATOR},
    )
    assert resp.status_code == 200
    assert "rsv_" in resp.text


@pytest.mark.anyio
async def test_create_api_key_role_override_lower(client, db_session):
    """Operator can create a key with viewer (lower) role override."""
    resp = await client.post(
        "/htmx/api-keys",
        data={"name": "lower-role-key", "role_override": ROLE_VIEWER},
    )
    assert resp.status_code == 200
    assert "rsv_" in resp.text


@pytest.mark.anyio
async def test_create_api_key_role_override_higher_rejected(client):
    """Operator cannot create a key with admin (higher) role override."""
    resp = await client.post(
        "/htmx/api-keys",
        data={"name": "admin-key", "role_override": "admin"},
    )
    assert resp.status_code == 200
    assert "Cannot create key with role" in resp.text
    assert "rsv_" not in resp.text


@pytest.mark.anyio
async def test_create_api_key_unauthenticated(unauth_client):
    """Unauthenticated POST is blocked by CSRF middleware (no token)."""
    resp = await unauth_client.post(
        "/htmx/api-keys",
        data={"name": "sneaky-key"},
        follow_redirects=False,
    )
    # CsrfMiddleware rejects before AuthRedirectMiddleware can redirect
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_create_api_key_viewer_cannot_set_operator_role(db_session, test_engine):
    """A viewer user cannot create a key with operator role override."""
    import os

    from app.config import get_settings
    from app.database import get_session
    from app.api.deps import verify_api_key
    from tests.conftest import get_test_settings, mock_verify_api_key

    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"
    get_settings.cache_clear()

    viewer_user = User(
        username="test-viewer",
        email="viewer@test.local",
        password_hash=hash_password("TestPass1!"),
        role=ROLE_VIEWER,
    )
    db_session.add(viewer_user)
    db_session.flush()

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[verify_api_key] = mock_verify_api_key

    csrf_token = generate_csrf_token()
    jwt_token = _make_test_jwt(
        user_id=str(viewer_user.id),
        username=viewer_user.username,
        role=viewer_user.role,
    )

    viewer_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-api-key", "X-CSRF-Token": csrf_token},
        cookies={"csrf_token": csrf_token, "access_token": jwt_token},
    )

    try:
        resp = await viewer_client.post(
            "/htmx/api-keys",
            data={"name": "escalated-key", "role_override": ROLE_OPERATOR},
        )
        assert resp.status_code == 200
        assert "Cannot create key with role" in resp.text
    finally:
        await viewer_client.aclose()
        app.dependency_overrides.clear()
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# DELETE /htmx/api-keys/{key_id} — revoke
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_revoke_api_key_success(client, db_session):
    """Revoking an owned key marks it inactive and returns updated list."""
    user = _get_test_user(db_session)
    key = _create_api_key(db_session, user.id, name="to-revoke")

    resp = await client.delete(f"/htmx/api-keys/{key.id}")
    assert resp.status_code == 200
    # Revoked key should no longer appear in the returned list
    assert "to-revoke" not in resp.text

    # Verify in DB
    db_session.refresh(key)
    assert key.is_active is False


@pytest.mark.anyio
async def test_revoke_api_key_not_found(client):
    """Revoking a non-existent key returns 404."""
    fake_id = uuid4()
    resp = await client.delete(f"/htmx/api-keys/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_revoke_api_key_wrong_user(client, db_session):
    """Cannot revoke a key owned by a different user (returns 404)."""
    other_user = User(
        username="other-user",
        email="other@test.local",
        password_hash=hash_password("TestPass1!"),
        role=ROLE_OPERATOR,
    )
    db_session.add(other_user)
    db_session.flush()

    key = _create_api_key(db_session, other_user.id, name="not-mine")

    resp = await client.delete(f"/htmx/api-keys/{key.id}")
    assert resp.status_code == 404

    # Key should still be active
    db_session.refresh(key)
    assert key.is_active is True


@pytest.mark.anyio
async def test_revoke_already_inactive_key(client, db_session):
    """Revoking an already-inactive key returns 404."""
    user = _get_test_user(db_session)
    key = _create_api_key(db_session, user.id, name="already-revoked", is_active=False)

    resp = await client.delete(f"/htmx/api-keys/{key.id}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_revoke_api_key_unauthenticated(unauth_client, db_session):
    """Unauthenticated DELETE is blocked by CSRF middleware (no token)."""
    fake_id = uuid4()
    resp = await unauth_client.delete(
        f"/htmx/api-keys/{fake_id}",
        follow_redirects=False,
    )
    # CsrfMiddleware rejects before AuthRedirectMiddleware can redirect
    assert resp.status_code == 403
