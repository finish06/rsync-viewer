"""Tests for OIDC Settings admin UI (specs/oidc-settings.md).

Covers: S-AC-001 through S-AC-014
"""

import os
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app.config import get_settings
from app.database import get_session
from app.main import app
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
_TEST_FERNET_KEY = Fernet.generate_key().decode()


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
    os.environ["SMTP_ENCRYPTION_KEY"] = _TEST_FERNET_KEY
    get_settings.cache_clear()

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings


def _cleanup():
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    os.environ.pop("SMTP_ENCRYPTION_KEY", None)


def _create_user(
    db_session: Session,
    username: str = "testuser",
    role: str = ROLE_ADMIN,
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
    from app.csrf import generate_csrf_token

    jwt_token = _make_jwt(str(user.id), user.username, user.role)
    csrf_token = generate_csrf_token()
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-CSRF-Token": csrf_token},
        cookies={"access_token": jwt_token, "csrf_token": csrf_token},
    )


# --- S-AC-008 / S-AC-009: Access control ---


class TestOidcSettingsAccess:
    """S-AC-008: Non-admin users cannot see Authentication section.
    S-AC-009: Non-admin users cannot access Authentication endpoints (403).
    """

    @pytest.mark.anyio
    async def test_sac009_operator_cannot_get_oidc_settings(
        self, test_engine, db_session
    ):
        _setup_overrides(db_session)
        operator = _create_user(db_session, "oidc-operator", ROLE_OPERATOR)

        async with _make_client(operator) as client:
            response = await client.get("/htmx/settings/auth")
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_sac009_viewer_cannot_get_oidc_settings(
        self, test_engine, db_session
    ):
        _setup_overrides(db_session)
        viewer = _create_user(db_session, "oidc-viewer", ROLE_VIEWER)

        async with _make_client(viewer) as client:
            response = await client.get("/htmx/settings/auth")
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_sac009_operator_cannot_post_oidc_settings(
        self, test_engine, db_session
    ):
        _setup_overrides(db_session)
        operator = _create_user(db_session, "oidc-op-post", ROLE_OPERATOR)

        async with _make_client(operator) as client:
            response = await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://evil.example.com",
                    "client_id": "evil",
                    "client_secret": "evil-secret",
                    "provider_name": "Evil",
                },
            )
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_sac009_operator_cannot_test_discovery(self, test_engine, db_session):
        _setup_overrides(db_session)
        operator = _create_user(db_session, "oidc-op-disc", ROLE_OPERATOR)

        async with _make_client(operator) as client:
            response = await client.post(
                "/htmx/settings/auth/test-discovery",
                data={"issuer_url": "https://auth.example.com"},
            )
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_sac008_admin_can_get_oidc_settings(self, test_engine, db_session):
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-admin", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.get("/htmx/settings/auth")
        _cleanup()

        assert response.status_code == 200
        assert "Issuer URL" in response.text or "issuer" in response.text.lower()


# --- S-AC-001: Admin configures OIDC provider via UI ---


class TestOidcSettingsSave:
    """S-AC-001: Admin can configure OIDC provider.
    S-AC-005: Client secret encrypted at rest.
    S-AC-012: Empty client secret preserves existing.
    """

    @pytest.mark.anyio
    async def test_sac001_admin_creates_oidc_config(self, test_engine, db_session):
        """Admin can save a new OIDC configuration."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-create", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://auth.example.com",
                    "client_id": "rsync-viewer",
                    "client_secret": "my-secret",
                    "provider_name": "PocketId",
                    "scopes": "openid email profile",
                },
            )
        _cleanup()

        assert response.status_code == 200
        assert "saved" in response.text.lower() or "success" in response.text.lower()

    @pytest.mark.anyio
    async def test_sac001_validation_rejects_missing_fields(
        self, test_engine, db_session
    ):
        """Required fields must be provided."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-validate", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "",
                    "client_id": "",
                    "client_secret": "secret",
                    "provider_name": "Test",
                },
            )
        _cleanup()

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_sac005_client_secret_encrypted_at_rest(
        self, test_engine, db_session
    ):
        """Client secret should be Fernet-encrypted in the database."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-encrypt", ROLE_ADMIN)

        async with _make_client(admin) as client:
            await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://auth.example.com",
                    "client_id": "rsync-viewer",
                    "client_secret": "plaintext-secret",
                    "provider_name": "PocketId",
                },
            )

        from app.services.oidc import get_oidc_config

        config = get_oidc_config(db_session)
        _cleanup()

        assert config is not None
        assert config.encrypted_client_secret != "plaintext-secret"
        assert len(config.encrypted_client_secret) > 0

    @pytest.mark.anyio
    async def test_sac006_client_secret_masked_in_response(
        self, test_engine, db_session
    ):
        """S-AC-006: Client secret displayed as masked dots in the UI."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-mask", ROLE_ADMIN)

        async with _make_client(admin) as client:
            await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://auth.example.com",
                    "client_id": "rsync-viewer",
                    "client_secret": "super-secret-value",
                    "provider_name": "PocketId",
                },
            )
            # Reload the form
            response = await client.get("/htmx/settings/auth")
        _cleanup()

        assert response.status_code == 200
        assert "super-secret-value" not in response.text
        assert "••••••••" in response.text

    @pytest.mark.anyio
    async def test_sac012_empty_secret_preserves_existing(
        self, test_engine, db_session
    ):
        """S-AC-012: Empty client secret on edit preserves existing encrypted value."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-preserve", ROLE_ADMIN)

        async with _make_client(admin) as client:
            # Create config with a secret
            await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://auth.example.com",
                    "client_id": "rsync-viewer",
                    "client_secret": "original-secret",
                    "provider_name": "PocketId",
                },
            )

            from app.services.oidc import get_oidc_config

            original_encrypted = get_oidc_config(db_session).encrypted_client_secret

            # Update with empty secret — should keep original
            await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://auth.example.com",
                    "client_id": "rsync-viewer",
                    "client_secret": "",
                    "provider_name": "Authelia",
                },
            )

        config = get_oidc_config(db_session)
        _cleanup()

        assert config.provider_name == "Authelia"
        assert config.encrypted_client_secret == original_encrypted


# --- S-AC-002 / S-AC-003: Enable/disable toggles ---


class TestOidcSettingsToggles:
    """S-AC-002: Admin can toggle OIDC enabled/disabled.
    S-AC-003: Admin can toggle Hide Local Login.
    """

    @pytest.mark.anyio
    async def test_sac002_enable_oidc(self, test_engine, db_session):
        """Admin can enable OIDC via toggle."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-enable", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://auth.example.com",
                    "client_id": "rsync-viewer",
                    "client_secret": "secret",
                    "provider_name": "PocketId",
                    "enabled": "on",
                },
            )

        from app.services.oidc import get_oidc_config

        config = get_oidc_config(db_session)
        _cleanup()

        assert response.status_code == 200
        assert config.enabled is True

    @pytest.mark.anyio
    async def test_sac002_disable_oidc(self, test_engine, db_session):
        """Admin can disable OIDC (toggle omitted from form = disabled)."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-disable", ROLE_ADMIN)

        async with _make_client(admin) as client:
            # Create enabled
            await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://auth.example.com",
                    "client_id": "rsync-viewer",
                    "client_secret": "secret",
                    "provider_name": "PocketId",
                    "enabled": "on",
                },
            )
            # Update without enabled checkbox — should disable
            await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://auth.example.com",
                    "client_id": "rsync-viewer",
                    "client_secret": "",
                    "provider_name": "PocketId",
                },
            )

        from app.services.oidc import get_oidc_config

        config = get_oidc_config(db_session)
        _cleanup()

        assert config.enabled is False

    @pytest.mark.anyio
    async def test_sac003_hide_local_login(self, test_engine, db_session):
        """Admin can toggle Hide Local Login."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-hide", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://auth.example.com",
                    "client_id": "rsync-viewer",
                    "client_secret": "secret",
                    "provider_name": "PocketId",
                    "enabled": "on",
                    "hide_local_login": "on",
                },
            )

        from app.services.oidc import get_oidc_config

        config = get_oidc_config(db_session)
        _cleanup()

        assert response.status_code == 200
        assert config.hide_local_login is True


# --- S-AC-007: Test OIDC Discovery ---


class TestOidcDiscovery:
    """S-AC-007: Admin can test OIDC discovery."""

    @pytest.mark.anyio
    async def test_sac007_discovery_success(self, test_engine, db_session):
        """Successful discovery shows endpoints."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-disc-ok", ROLE_ADMIN)

        mock_discovery = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "userinfo_endpoint": "https://auth.example.com/userinfo",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
        }

        with patch(
            "app.routes.settings.fetch_discovery",
            new_callable=AsyncMock,
            return_value=mock_discovery,
        ):
            async with _make_client(admin) as client:
                response = await client.post(
                    "/htmx/settings/auth/test-discovery",
                    data={"issuer_url": "https://auth.example.com"},
                )
        _cleanup()

        assert response.status_code == 200
        assert "authorization_endpoint" in response.text or "authorize" in response.text

    @pytest.mark.anyio
    async def test_sac007_discovery_failure(self, test_engine, db_session):
        """Failed discovery shows error message."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-disc-fail", ROLE_ADMIN)

        with patch(
            "app.routes.settings.fetch_discovery",
            new_callable=AsyncMock,
            side_effect=Exception("Could not reach issuer URL"),
        ):
            async with _make_client(admin) as client:
                response = await client.post(
                    "/htmx/settings/auth/test-discovery",
                    data={"issuer_url": "https://nonexistent.example.com"},
                )
        _cleanup()

        assert response.status_code == 200
        assert "error" in response.text.lower() or "failed" in response.text.lower()

    @pytest.mark.anyio
    async def test_sac011_save_allowed_even_if_discovery_fails(
        self, test_engine, db_session
    ):
        """S-AC-011: Save is allowed even if discovery test fails."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-save-no-disc", ROLE_ADMIN)

        async with _make_client(admin) as client:
            # Save without testing discovery — should succeed
            response = await client.post(
                "/htmx/settings/auth",
                data={
                    "issuer_url": "https://not-yet-live.example.com",
                    "client_id": "rsync-viewer",
                    "client_secret": "secret",
                    "provider_name": "Future Provider",
                },
            )
        _cleanup()

        assert response.status_code == 200
        assert "saved" in response.text.lower() or "success" in response.text.lower()


# --- S-AC-013: Info note about FORCE_LOCAL_LOGIN ---


class TestOidcSettingsInfoNote:
    """S-AC-013: Info note about FORCE_LOCAL_LOGIN safety fallback."""

    @pytest.mark.anyio
    async def test_sac013_info_note_visible(self, test_engine, db_session):
        """The OIDC settings form shows info about FORCE_LOCAL_LOGIN."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-info", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.get("/htmx/settings/auth")
        _cleanup()

        assert response.status_code == 200
        assert "FORCE_LOCAL_LOGIN" in response.text


# --- S-AC-016 / S-AC-017: Dark mode theming ---


class TestOidcSettingsDarkMode:
    """S-AC-016: Info boxes render correctly in dark mode.
    S-AC-017: No inline bg-secondary with hardcoded fallback.
    """

    @pytest.mark.anyio
    async def test_sac017_no_inline_bg_secondary(self, test_engine, db_session):
        """S-AC-017: No inline background: var(--bg-secondary, #f5f5f5) styles."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-dark-mode", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.get("/htmx/settings/auth")
        _cleanup()

        assert response.status_code == 200
        html = response.text
        # Must not contain inline bg-secondary with hardcoded light fallback
        assert "var(--bg-secondary, #f5f5f5)" not in html

    @pytest.mark.anyio
    async def test_sac016_info_boxes_use_css_class(self, test_engine, db_session):
        """S-AC-016: Info boxes use a CSS class instead of inline styles."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-css-class", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.get("/htmx/settings/auth")
        _cleanup()

        assert response.status_code == 200
        html = response.text
        assert "info-box" in html


# --- S-AC-010: OIDC login flow reads config from DB ---
# (This will be tested in test_oidc_auth.py when the auth flow is implemented)
