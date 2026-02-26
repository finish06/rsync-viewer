"""Tests for per-user API key management.

Covers: AC-011, AC-012
"""

import os
from datetime import timedelta
from uuid import uuid4

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, select

from app.api.deps import hash_api_key
from app.config import get_settings
from app.database import get_session
from app.main import app
from app.models.sync_log import ApiKey
from app.models.user import User
from app.services.auth import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    hash_password,
)
from app.utils import utc_now

_TEST_SECRET = "test-secret-key"
_TEST_ALGORITHM = "HS256"


def _make_jwt(user_id: str, username: str, role: str) -> str:
    now = utc_now()
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    return pyjwt.encode(payload, _TEST_SECRET, algorithm=_TEST_ALGORITHM)


def _setup_overrides(db_session: Session):
    from tests.conftest import get_test_settings

    os.environ["SECRET_KEY"] = _TEST_SECRET
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"
    get_settings.cache_clear()

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings


def _cleanup():
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _create_user(
    db_session: Session,
    username: str = "testuser",
    role: str = ROLE_OPERATOR,
) -> User:
    user = User(
        username=username,
        email=f"{username}@test.local",
        password_hash=hash_password("TestPass1!"),
        role=role,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _make_client(user: User) -> AsyncClient:
    jwt_token = _make_jwt(str(user.id), user.username, user.role)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"access_token": jwt_token},
    )


# --- AC-011: Per-user API keys CRUD ---


class TestApiKeyGeneration:
    """AC-011: Users can generate API keys."""

    @pytest.mark.anyio
    async def test_ac011_generate_api_key(self, test_engine, db_session):
        """POST /api/v1/api-keys should create a key for the authenticated user."""
        _setup_overrides(db_session)
        user = _create_user(db_session, "keygen-user", ROLE_OPERATOR)
        async with _make_client(user) as client:
            response = await client.post(
                "/api/v1/api-keys",
                json={"name": "My Script Key"},
            )
        _cleanup()

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Script Key"
        assert "key" in data  # plaintext key shown once
        assert data["key_prefix"]  # prefix for identification
        assert data["role"] == ROLE_OPERATOR  # inherits user's role
        assert "id" in data

    @pytest.mark.anyio
    async def test_ac011_generated_key_prefix(self, test_engine, db_session):
        """Generated key should have a prefix for identification."""
        _setup_overrides(db_session)
        user = _create_user(db_session, "prefix-user", ROLE_OPERATOR)
        async with _make_client(user) as client:
            response = await client.post(
                "/api/v1/api-keys",
                json={"name": "Prefix Test"},
            )
        _cleanup()

        data = response.json()
        assert data["key"].startswith("rsv_")
        assert data["key_prefix"] == data["key"][:8]

    @pytest.mark.anyio
    async def test_ac011_key_stored_hashed(self, test_engine, db_session):
        """Only the hash should be stored in the database, not the plaintext key."""
        _setup_overrides(db_session)
        user = _create_user(db_session, "hash-user", ROLE_OPERATOR)
        async with _make_client(user) as client:
            response = await client.post(
                "/api/v1/api-keys",
                json={"name": "Hash Test"},
            )
        _cleanup()

        data = response.json()
        raw_key = data["key"]

        # Check database — key_hash should not equal plaintext
        api_key = db_session.exec(
            select(ApiKey).where(ApiKey.name == "Hash Test")
        ).first()
        assert api_key is not None
        assert api_key.key_hash != raw_key
        assert api_key.key_hash.startswith("$2b$")  # bcrypt

    @pytest.mark.anyio
    async def test_ac011_key_linked_to_user(self, test_engine, db_session):
        """Generated key should have user_id set to the authenticated user."""
        _setup_overrides(db_session)
        user = _create_user(db_session, "linked-user", ROLE_OPERATOR)
        async with _make_client(user) as client:
            response = await client.post(
                "/api/v1/api-keys",
                json={"name": "Link Test"},
            )
        _cleanup()

        data = response.json()
        api_key = db_session.get(ApiKey, data["id"])
        assert api_key is not None
        assert api_key.user_id == user.id


class TestApiKeyListing:
    """AC-011: Users can list their API keys."""

    @pytest.mark.anyio
    async def test_ac011_list_own_keys(self, test_engine, db_session):
        """GET /api/v1/api-keys should return only the user's keys."""
        _setup_overrides(db_session)
        user_a = _create_user(db_session, "user-a", ROLE_OPERATOR)
        user_b = _create_user(db_session, "user-b", ROLE_OPERATOR)

        # Create keys for both users
        async with _make_client(user_a) as client_a:
            await client_a.post("/api/v1/api-keys", json={"name": "Key A"})
        async with _make_client(user_b) as client_b:
            await client_b.post("/api/v1/api-keys", json={"name": "Key B"})

        # User A should only see their own key
        async with _make_client(user_a) as client_a:
            response = await client_a.get("/api/v1/api-keys")
        _cleanup()

        assert response.status_code == 200
        keys = response.json()
        assert len(keys) == 1
        assert keys[0]["name"] == "Key A"

    @pytest.mark.anyio
    async def test_ac011_list_keys_no_plaintext(self, test_engine, db_session):
        """Listed keys should NOT include the plaintext key."""
        _setup_overrides(db_session)
        user = _create_user(db_session, "noraw-user", ROLE_OPERATOR)
        async with _make_client(user) as client:
            await client.post("/api/v1/api-keys", json={"name": "No Raw"})
            response = await client.get("/api/v1/api-keys")
        _cleanup()

        keys = response.json()
        assert len(keys) == 1
        assert "key" not in keys[0]  # no plaintext key in list
        assert "key_hash" not in keys[0]  # no hash either
        assert "key_prefix" in keys[0]  # prefix for identification

    @pytest.mark.anyio
    async def test_ac011_admin_lists_all_keys(self, test_engine, db_session):
        """Admin should be able to list all users' keys."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-lister", ROLE_ADMIN)
        operator = _create_user(db_session, "op-lister", ROLE_OPERATOR)

        async with _make_client(admin) as client:
            await client.post("/api/v1/api-keys", json={"name": "Admin Key"})
        async with _make_client(operator) as client:
            await client.post("/api/v1/api-keys", json={"name": "Operator Key"})

        # Admin with ?all=true sees all keys
        async with _make_client(admin) as client:
            response = await client.get("/api/v1/api-keys?all=true")
        _cleanup()

        assert response.status_code == 200
        keys = response.json()
        assert len(keys) == 2


class TestApiKeyRevocation:
    """AC-011: Users can revoke their API keys."""

    @pytest.mark.anyio
    async def test_ac011_revoke_own_key(self, test_engine, db_session):
        """DELETE /api/v1/api-keys/{id} should revoke the user's key."""
        _setup_overrides(db_session)
        user = _create_user(db_session, "revoke-user", ROLE_OPERATOR)
        async with _make_client(user) as client:
            create_resp = await client.post(
                "/api/v1/api-keys", json={"name": "To Revoke"}
            )
            key_id = create_resp.json()["id"]
            response = await client.delete(f"/api/v1/api-keys/{key_id}")
        _cleanup()

        assert response.status_code == 204

    @pytest.mark.anyio
    async def test_ac011_revoked_key_not_in_list(self, test_engine, db_session):
        """Revoked key should not appear in active key listing."""
        _setup_overrides(db_session)
        user = _create_user(db_session, "revokedlist-user", ROLE_OPERATOR)
        async with _make_client(user) as client:
            create_resp = await client.post(
                "/api/v1/api-keys", json={"name": "Gone Key"}
            )
            key_id = create_resp.json()["id"]
            await client.delete(f"/api/v1/api-keys/{key_id}")
            response = await client.get("/api/v1/api-keys")
        _cleanup()

        keys = response.json()
        assert len(keys) == 0

    @pytest.mark.anyio
    async def test_ac011_cannot_revoke_others_key(self, test_engine, db_session):
        """Non-admin user cannot revoke another user's key."""
        _setup_overrides(db_session)
        user_a = _create_user(db_session, "owner-a", ROLE_OPERATOR)
        user_b = _create_user(db_session, "thief-b", ROLE_OPERATOR)

        async with _make_client(user_a) as client:
            create_resp = await client.post(
                "/api/v1/api-keys", json={"name": "A's Key"}
            )
            key_id = create_resp.json()["id"]

        async with _make_client(user_b) as client:
            response = await client.delete(f"/api/v1/api-keys/{key_id}")
        _cleanup()

        assert response.status_code == 404  # Not found (not their key)

    @pytest.mark.anyio
    async def test_ac011_admin_can_revoke_any_key(self, test_engine, db_session):
        """Admin can revoke any user's key."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-revoker", ROLE_ADMIN)
        operator = _create_user(db_session, "op-target", ROLE_OPERATOR)

        async with _make_client(operator) as client:
            create_resp = await client.post("/api/v1/api-keys", json={"name": "Op Key"})
            key_id = create_resp.json()["id"]

        async with _make_client(admin) as client:
            response = await client.delete(f"/api/v1/api-keys/{key_id}")
        _cleanup()

        assert response.status_code == 204

    @pytest.mark.anyio
    async def test_ac011_revoke_nonexistent_returns_404(self, test_engine, db_session):
        """Revoking a non-existent key returns 404."""
        _setup_overrides(db_session)
        user = _create_user(db_session, "ghost-revoker", ROLE_OPERATOR)
        fake_id = str(uuid4())
        async with _make_client(user) as client:
            response = await client.delete(f"/api/v1/api-keys/{fake_id}")
        _cleanup()

        assert response.status_code == 404


# --- AC-012: API key role scoping ---


class TestApiKeyRoleScoping:
    """AC-012: API key permissions are scoped to the user's role."""

    @pytest.mark.anyio
    async def test_ac012_key_inherits_user_role(self, test_engine, db_session):
        """Key without role_override inherits user's role."""
        _setup_overrides(db_session)
        user = _create_user(db_session, "role-inherit", ROLE_OPERATOR)
        async with _make_client(user) as client:
            response = await client.post(
                "/api/v1/api-keys", json={"name": "Inherit Key"}
            )
        _cleanup()

        assert response.status_code == 201
        assert response.json()["role"] == ROLE_OPERATOR

    @pytest.mark.anyio
    async def test_ac012_role_override_below_user_role(self, test_engine, db_session):
        """Key can be scoped to a lower role than the user's."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-scoper", ROLE_ADMIN)
        async with _make_client(admin) as client:
            response = await client.post(
                "/api/v1/api-keys",
                json={"name": "Viewer Key", "role_override": ROLE_VIEWER},
            )
        _cleanup()

        assert response.status_code == 201
        assert response.json()["role"] == ROLE_VIEWER

    @pytest.mark.anyio
    async def test_ac012_role_override_above_user_role_rejected(
        self, test_engine, db_session
    ):
        """Key cannot be scoped higher than the user's role."""
        _setup_overrides(db_session)
        viewer = _create_user(db_session, "viewer-escalator", ROLE_VIEWER)
        async with _make_client(viewer) as client:
            response = await client.post(
                "/api/v1/api-keys",
                json={"name": "Escalate Key", "role_override": ROLE_ADMIN},
            )
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_ac012_api_key_auth_uses_user_role(self, test_engine, db_session):
        """When authenticating with a per-user API key, the user's role is enforced."""
        _setup_overrides(db_session)
        viewer = _create_user(db_session, "viewer-api", ROLE_VIEWER)

        # Create a key for the viewer
        async with _make_client(viewer) as client:
            create_resp = await client.post(
                "/api/v1/api-keys", json={"name": "Viewer API Key"}
            )
        raw_key = create_resp.json()["key"]

        # Use the key to try to submit a sync log (requires operator)
        unauthenticated_client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )
        now = utc_now()
        async with unauthenticated_client as ua_client:
            response = await ua_client.post(
                "/api/v1/sync-logs",
                json={
                    "source_name": "test",
                    "start_time": (now - timedelta(minutes=1)).isoformat(),
                    "end_time": now.isoformat(),
                    "raw_content": "sent 100 bytes  received 200 bytes  300 bytes/sec\ntotal size is 1000  speedup is 10.00",
                },
                headers={"X-API-Key": raw_key},
            )
        _cleanup()

        # Viewer role should be denied from submitting sync logs
        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_ac012_role_override_enforced_on_auth(self, test_engine, db_session):
        """When a key has role_override, that role is used for permission checks."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-override", ROLE_ADMIN)

        # Create a viewer-scoped key for the admin
        async with _make_client(admin) as client:
            create_resp = await client.post(
                "/api/v1/api-keys",
                json={"name": "Viewer Scoped", "role_override": ROLE_VIEWER},
            )
        raw_key = create_resp.json()["key"]

        # Use the viewer-scoped key to try to submit a sync log
        unauthenticated_client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )
        now = utc_now()
        async with unauthenticated_client as ua_client:
            response = await ua_client.post(
                "/api/v1/sync-logs",
                json={
                    "source_name": "test",
                    "start_time": (now - timedelta(minutes=1)).isoformat(),
                    "end_time": now.isoformat(),
                    "raw_content": "sent 100 bytes  received 200 bytes  300 bytes/sec\ntotal size is 1000  speedup is 10.00",
                },
                headers={"X-API-Key": raw_key},
            )
        _cleanup()

        # Viewer role override means 403 on sync log submission
        assert response.status_code == 403


class TestLegacyApiKeyCompat:
    """AC-012: Legacy keys (no user_id) remain functional."""

    @pytest.mark.anyio
    async def test_ac012_legacy_key_no_user_id_works(self, test_engine, db_session):
        """API key without user_id should still authenticate (operator-level)."""
        _setup_overrides(db_session)

        # Create a legacy key (no user_id)
        legacy_key_raw = "legacy-test-key-123"
        legacy_key = ApiKey(
            id=uuid4(),
            key_hash=hash_api_key(legacy_key_raw),
            key_prefix="lega",
            name="Legacy Key",
            is_active=True,
            user_id=None,  # legacy — no user
        )
        db_session.add(legacy_key)
        db_session.flush()

        # Use the legacy key to submit a sync log
        unauthenticated_client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )
        now = utc_now()
        async with unauthenticated_client as ua_client:
            response = await ua_client.post(
                "/api/v1/sync-logs",
                json={
                    "source_name": "legacy-test",
                    "start_time": (now - timedelta(minutes=1)).isoformat(),
                    "end_time": now.isoformat(),
                    "raw_content": "sent 100 bytes  received 200 bytes  300 bytes/sec\ntotal size is 1000  speedup is 10.00",
                },
                headers={"X-API-Key": legacy_key_raw},
            )
        _cleanup()

        # Legacy keys should work at operator level
        assert response.status_code == 201


class TestApiKeyAuth:
    """AC-011: Authentication requirements for API key endpoints."""

    @pytest.mark.anyio
    async def test_ac011_generate_requires_auth(self, test_engine, db_session):
        """POST /api/v1/api-keys without auth returns 401."""
        _setup_overrides(db_session)
        unauthenticated_client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )
        async with unauthenticated_client as client:
            response = await client.post("/api/v1/api-keys", json={"name": "No Auth"})
        _cleanup()

        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_ac011_list_requires_auth(self, test_engine, db_session):
        """GET /api/v1/api-keys without auth returns 401."""
        _setup_overrides(db_session)
        unauthenticated_client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )
        async with unauthenticated_client as client:
            response = await client.get("/api/v1/api-keys")
        _cleanup()

        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_ac011_viewer_can_generate_keys(self, test_engine, db_session):
        """Viewers should be able to generate their own API keys."""
        _setup_overrides(db_session)
        viewer = _create_user(db_session, "viewer-keygen", ROLE_VIEWER)
        async with _make_client(viewer) as client:
            response = await client.post(
                "/api/v1/api-keys", json={"name": "Viewer Key"}
            )
        _cleanup()

        assert response.status_code == 201
        assert response.json()["role"] == ROLE_VIEWER
