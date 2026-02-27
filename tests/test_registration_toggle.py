"""Tests for REGISTRATION_ENABLED toggle.

Covers: registration disable feature across API and UI endpoints.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import get_session
from app.main import app

_TEST_SECRET = "test-secret-key"


def _setup_disabled(db_session):
    """Set up overrides with registration DISABLED."""
    os.environ["SECRET_KEY"] = _TEST_SECRET
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"
    os.environ["REGISTRATION_ENABLED"] = "false"
    get_settings.cache_clear()

    from tests.conftest import get_test_settings

    # Build a custom settings factory that also disables registration
    _base = get_test_settings()

    def _disabled_settings():
        from app.config import Settings

        return Settings(
            app_name=_base.app_name,
            debug=_base.debug,
            database_url=_base.database_url,
            secret_key=_base.secret_key,
            default_api_key=_base.default_api_key,
            registration_enabled=False,
        )

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = _disabled_settings


def _setup_enabled(db_session):
    """Set up overrides with registration ENABLED."""
    os.environ["SECRET_KEY"] = _TEST_SECRET
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"
    os.environ["REGISTRATION_ENABLED"] = "true"
    get_settings.cache_clear()

    from tests.conftest import get_test_settings

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings


def _cleanup():
    app.dependency_overrides.clear()
    os.environ.pop("REGISTRATION_ENABLED", None)
    get_settings.cache_clear()


class TestRegistrationDisabled:
    """Tests for when REGISTRATION_ENABLED=false."""

    @pytest.mark.anyio
    async def test_get_register_shows_disabled_message(self, test_engine, db_session):
        """GET /register shows disabled message when registration is off."""
        _setup_disabled(db_session)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/register")

        _cleanup()

        assert response.status_code == 200
        assert "disabled" in response.text.lower()

    @pytest.mark.anyio
    async def test_post_register_returns_403_when_disabled(
        self, test_engine, db_session
    ):
        """POST /register returns 403 when registration is off."""
        _setup_disabled(db_session)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/register",
                data={
                    "username": "newuser",
                    "email": "new@example.com",
                    "password": "StrongPass1!",
                    "password_confirm": "StrongPass1!",
                },
            )

        _cleanup()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_api_register_returns_403_when_disabled(
        self, test_engine, db_session
    ):
        """POST /api/v1/auth/register returns 403 when registration is off."""
        _setup_disabled(db_session)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "newuser",
                    "email": "new@example.com",
                    "password": "StrongPass1!",
                },
            )

        _cleanup()

        assert response.status_code == 403


class TestRegistrationEnabled:
    """Tests for when REGISTRATION_ENABLED=true (default)."""

    @pytest.mark.anyio
    async def test_get_register_shows_form_when_enabled(self, test_engine, db_session):
        """GET /register shows registration form when enabled."""
        _setup_enabled(db_session)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/register")

        _cleanup()

        assert response.status_code == 200
        # The form should be visible, not the disabled message
        assert "username" in response.text.lower()
        assert "password" in response.text.lower()
