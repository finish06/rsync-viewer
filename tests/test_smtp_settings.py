"""Tests for SMTP settings HTMX endpoints.

Covers: AC-001, AC-002, AC-003, AC-006, AC-007, AC-009, AC-010
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


class TestSmtpSettingsAccess:
    """AC-006: Non-admin users cannot access SMTP settings."""

    @pytest.mark.anyio
    async def test_ac006_operator_cannot_get_smtp_settings(
        self, test_engine, db_session
    ):
        _setup_overrides(db_session)
        operator = _create_user(db_session, "operator-user", ROLE_OPERATOR)

        async with _make_client(operator) as client:
            response = await client.get("/htmx/smtp-settings")
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_ac006_viewer_cannot_get_smtp_settings(self, test_engine, db_session):
        _setup_overrides(db_session)
        viewer = _create_user(db_session, "viewer-user", ROLE_VIEWER)

        async with _make_client(viewer) as client:
            response = await client.get("/htmx/smtp-settings")
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_ac006_operator_cannot_post_smtp_settings(
        self, test_engine, db_session
    ):
        _setup_overrides(db_session)
        operator = _create_user(db_session, "operator-post", ROLE_OPERATOR)

        async with _make_client(operator) as client:
            response = await client.post(
                "/htmx/smtp-settings",
                data={
                    "host": "smtp.evil.com",
                    "port": "587",
                    "encryption": "starttls",
                    "from_address": "evil@example.com",
                },
            )
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_ac006_operator_cannot_send_test_email(self, test_engine, db_session):
        _setup_overrides(db_session)
        operator = _create_user(db_session, "operator-test", ROLE_OPERATOR)

        async with _make_client(operator) as client:
            response = await client.post(
                "/htmx/smtp-settings/test",
                data={"test_email": "test@example.com"},
            )
        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_ac006_admin_can_get_smtp_settings(self, test_engine, db_session):
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-user", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.get("/htmx/smtp-settings")
        _cleanup()

        assert response.status_code == 200
        assert "SMTP Host" in response.text


class TestSmtpSettingsSave:
    """AC-001, AC-002, AC-009: Create and edit SMTP configuration."""

    @pytest.mark.anyio
    async def test_ac001_admin_creates_smtp_config(self, test_engine, db_session):
        """Admin can save a new SMTP configuration."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-create", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/smtp-settings",
                data={
                    "host": "smtp.example.com",
                    "port": "587",
                    "username": "user@example.com",
                    "password": "smtp-password",
                    "encryption": "starttls",
                    "from_address": "noreply@example.com",
                    "from_name": "Rsync Viewer",
                },
            )
        _cleanup()

        assert response.status_code == 200
        assert "SMTP configuration saved" in response.text
        assert "smtp.example.com" in response.text

    @pytest.mark.anyio
    async def test_ac001_validation_rejects_missing_fields(
        self, test_engine, db_session
    ):
        """Required fields (host, port, from_address) must be provided."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-validate", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/smtp-settings",
                data={
                    "host": "",
                    "port": "587",
                    "encryption": "starttls",
                    "from_address": "",
                },
            )
        _cleanup()

        assert response.status_code == 422
        assert "required" in response.text.lower()

    @pytest.mark.anyio
    async def test_ac001_validation_rejects_invalid_port(self, test_engine, db_session):
        """Port must be a number between 1 and 65535."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-port", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/smtp-settings",
                data={
                    "host": "smtp.example.com",
                    "port": "99999",
                    "encryption": "starttls",
                    "from_address": "noreply@example.com",
                },
            )
        _cleanup()

        assert response.status_code == 422
        assert "port" in response.text.lower()

    @pytest.mark.anyio
    async def test_ac002_admin_edits_smtp_config(self, test_engine, db_session):
        """Admin can update existing SMTP config without changing password."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-edit", ROLE_ADMIN)

        async with _make_client(admin) as client:
            # First, create a config
            await client.post(
                "/htmx/smtp-settings",
                data={
                    "host": "smtp.old.com",
                    "port": "587",
                    "username": "user@old.com",
                    "password": "old-password",
                    "encryption": "starttls",
                    "from_address": "old@example.com",
                    "from_name": "Old Name",
                },
            )

            # Then update it — empty password should keep old one
            response = await client.post(
                "/htmx/smtp-settings",
                data={
                    "host": "smtp.new.com",
                    "port": "465",
                    "username": "user@new.com",
                    "password": "",
                    "encryption": "ssl_tls",
                    "from_address": "new@example.com",
                    "from_name": "New Name",
                },
            )
        _cleanup()

        assert response.status_code == 200
        assert "smtp.new.com" in response.text
        assert "SMTP configuration saved" in response.text

    @pytest.mark.anyio
    async def test_ac007_password_masked_in_response(self, test_engine, db_session):
        """Password should show masked placeholder, not actual value."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-mask", ROLE_ADMIN)

        async with _make_client(admin) as client:
            # Save config with password
            await client.post(
                "/htmx/smtp-settings",
                data={
                    "host": "smtp.example.com",
                    "port": "587",
                    "password": "super-secret-password",
                    "encryption": "starttls",
                    "from_address": "noreply@example.com",
                },
            )

            # Load the form again
            response = await client.get("/htmx/smtp-settings")
        _cleanup()

        assert response.status_code == 200
        # Password should NOT appear in plaintext
        assert "super-secret-password" not in response.text
        # Masked placeholder should appear
        assert "••••••••" in response.text


class TestSmtpTestEmail:
    """AC-003, AC-010: Test email functionality."""

    @pytest.mark.anyio
    async def test_ac003_test_email_requires_recipient(self, test_engine, db_session):
        """Test email requires a recipient address."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-test-empty", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/smtp-settings/test",
                data={"test_email": ""},
            )
        _cleanup()

        assert response.status_code == 422
        assert "email address" in response.text.lower()

    @pytest.mark.anyio
    @patch("app.main.send_test_email_async", new_callable=AsyncMock)
    async def test_ac003_test_email_success(self, mock_send, test_engine, db_session):
        """Successful test email returns success message."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-test-ok", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/smtp-settings/test",
                data={"test_email": "recipient@example.com"},
            )
        _cleanup()

        assert response.status_code == 200
        assert "sent successfully" in response.text
        assert "recipient@example.com" in response.text
        mock_send.assert_called_once()

    @pytest.mark.anyio
    @patch(
        "app.main.send_test_email_async",
        new_callable=AsyncMock,
        side_effect=ValueError("SMTP is not configured"),
    )
    async def test_ac010_test_email_shows_error_on_failure(
        self, mock_send, test_engine, db_session
    ):
        """Failed test email displays error message."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-test-fail", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/smtp-settings/test",
                data={"test_email": "recipient@example.com"},
            )
        _cleanup()

        assert response.status_code == 400
        assert "SMTP is not configured" in response.text

    @pytest.mark.anyio
    async def test_ac008_test_email_fails_when_no_config_saved(
        self, test_engine, db_session
    ):
        """Sending test email with no SMTP config saved returns error."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "admin-no-config", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post(
                "/htmx/smtp-settings/test",
                data={"test_email": "recipient@example.com"},
            )
        _cleanup()

        assert response.status_code in (400, 500)
        assert (
            "smtp" in response.text.lower() or "not configured" in response.text.lower()
        )
