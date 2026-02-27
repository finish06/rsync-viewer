"""Tests for REGISTRATION_ENABLED toggle.

Covers: registration disable feature across API and UI endpoints.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.database import get_session
from app.main import app

_TEST_SECRET = "test-secret-key"
_TEST_ALGORITHM = "HS256"


def _get_settings_registration_disabled() -> Settings:
    """Settings with registration disabled."""
    return Settings(
        app_name="Rsync Log Viewer Test",
        debug=True,
        database_url="postgresql+psycopg://postgres:postgres@localhost:5433/rsync_viewer_test",
        secret_key=_TEST_SECRET,
        default_api_key="test-api-key",
        registration_enabled=False,
    )


def _get_settings_registration_enabled() -> Settings:
    """Settings with registration enabled (default)."""
    return Settings(
        app_name="Rsync Log Viewer Test",
        debug=True,
        database_url="postgresql+psycopg://postgres:postgres@localhost:5433/rsync_viewer_test",
        secret_key=_TEST_SECRET,
        default_api_key="test-api-key",
        registration_enabled=True,
    )


class TestRegistrationDisabled:
    """Tests for when REGISTRATION_ENABLED=false."""

    @pytest.mark.anyio
    async def test_get_register_shows_disabled_message(self, test_engine, db_session):
        """GET /register shows disabled message when registration is off."""
        os.environ["SECRET_KEY"] = _TEST_SECRET
        os.environ["DEBUG"] = "true"
        get_settings.cache_clear()

        def get_test_session():
            yield db_session

        app.dependency_overrides[get_session] = get_test_session
        app.dependency_overrides[get_settings] = _get_settings_registration_disabled

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/register")

        app.dependency_overrides.clear()
        get_settings.cache_clear()

        assert response.status_code == 200
        assert "disabled" in response.text.lower()

    @pytest.mark.anyio
    async def test_post_register_returns_403_when_disabled(
        self, test_engine, db_session
    ):
        """POST /register returns 403 when registration is off."""
        os.environ["SECRET_KEY"] = _TEST_SECRET
        os.environ["DEBUG"] = "true"
        get_settings.cache_clear()

        def get_test_session():
            yield db_session

        app.dependency_overrides[get_session] = get_test_session
        app.dependency_overrides[get_settings] = _get_settings_registration_disabled

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

        app.dependency_overrides.clear()
        get_settings.cache_clear()

        assert response.status_code == 403

    @pytest.mark.anyio
    async def test_api_register_returns_403_when_disabled(
        self, test_engine, db_session
    ):
        """POST /api/v1/auth/register returns 403 when registration is off."""
        os.environ["SECRET_KEY"] = _TEST_SECRET
        os.environ["DEBUG"] = "true"
        get_settings.cache_clear()

        def get_test_session():
            yield db_session

        app.dependency_overrides[get_session] = get_test_session
        app.dependency_overrides[get_settings] = _get_settings_registration_disabled

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

        app.dependency_overrides.clear()
        get_settings.cache_clear()

        assert response.status_code == 403


class TestRegistrationEnabled:
    """Tests for when REGISTRATION_ENABLED=true (default)."""

    @pytest.mark.anyio
    async def test_get_register_shows_form_when_enabled(self, test_engine, db_session):
        """GET /register shows registration form when enabled."""
        os.environ["SECRET_KEY"] = _TEST_SECRET
        os.environ["DEBUG"] = "true"
        get_settings.cache_clear()

        def get_test_session():
            yield db_session

        app.dependency_overrides[get_session] = get_test_session
        app.dependency_overrides[get_settings] = _get_settings_registration_enabled

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/register")

        app.dependency_overrides.clear()
        get_settings.cache_clear()

        assert response.status_code == 200
        # The form should be visible, not the disabled message
        assert "username" in response.text.lower()
        assert "password" in response.text.lower()
