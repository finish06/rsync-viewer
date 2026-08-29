"""Tests for specs/settings-ui.md AC-001–AC-009 — settings and changelog JSON APIs."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from sqlmodel import Session, select

from app.config import get_settings
from app.models.oidc_config import OidcConfig
from app.models.smtp_config import SmtpConfig
from app.models.sync_log import ApiKey
from app.models.synthetic_check_config import SyntheticCheckConfig
from app.models.user import User
from app.services.auth import ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER, hash_password
from tests.test_rbac import (
    _make_bearer_client,
    _make_cookie_client,
    _make_unauth_client,
)

FERNET_KEY = Fernet.generate_key().decode()


@pytest.fixture
def encryption_key():
    previous = os.environ.get("SMTP_ENCRYPTION_KEY")
    os.environ["SMTP_ENCRYPTION_KEY"] = FERNET_KEY
    get_settings.cache_clear()
    yield FERNET_KEY
    if previous is None:
        os.environ.pop("SMTP_ENCRYPTION_KEY", None)
    else:
        os.environ["SMTP_ENCRYPTION_KEY"] = previous
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def clean_config_rows(db_session: Session):
    for model in (SmtpConfig, OidcConfig, SyntheticCheckConfig):
        for row in db_session.exec(select(model)).all():
            db_session.delete(row)
    db_session.commit()


def _user(db_session, username, role) -> User:
    user = User(
        username=username,
        email=f"{username}@test.com",
        password_hash=hash_password("Passw0rd!x"),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin(db_session):
    return _user(db_session, "settings_admin", ROLE_ADMIN)


@pytest.fixture
def operator(db_session):
    return _user(db_session, "settings_operator", ROLE_OPERATOR)


@pytest.fixture
def viewer(db_session):
    return _user(db_session, "settings_viewer", ROLE_VIEWER)


SMTP_BODY = {
    "host": "smtp.example.com",
    "port": 587,
    "username": "alerts",
    "password": "s3cret",
    "encryption": "starttls",
    "from_address": "alerts@example.com",
    "from_name": "Rsync Viewer",
}


class TestAC001to003Smtp:
    async def test_ac001_unconfigured_read(self, db_session, admin, encryption_key):
        client = _make_cookie_client(db_session, admin)
        resp = await client.get("/api/v1/settings/smtp")
        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is False
        assert body["has_password"] is False
        assert body["encryption_key_configured"] is True
        assert "password" not in body and "encrypted_password" not in body

    async def test_ac002_save_then_read_hides_secret(
        self, db_session, admin, encryption_key
    ):
        client = _make_cookie_client(db_session, admin)
        resp = await client.put("/api/v1/settings/smtp", json=SMTP_BODY)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["configured"] is True
        assert body["host"] == "smtp.example.com"
        assert body["has_password"] is True
        assert "s3cret" not in resp.text

        # Saving again without a password keeps the stored one
        again = {**SMTP_BODY, "password": "", "from_name": "Alerts"}
        resp = await client.put("/api/v1/settings/smtp", json=again)
        assert resp.status_code == 200
        assert resp.json()["has_password"] is True
        assert resp.json()["from_name"] == "Alerts"
        row = db_session.exec(select(SmtpConfig)).one()
        assert row.encrypted_password and "s3cret" not in row.encrypted_password

    async def test_ac002_validation(self, db_session, admin, encryption_key):
        client = _make_cookie_client(db_session, admin)
        assert (
            await client.put("/api/v1/settings/smtp", json={**SMTP_BODY, "port": 70000})
        ).status_code == 422
        assert (
            await client.put(
                "/api/v1/settings/smtp", json={**SMTP_BODY, "encryption": "tls13"}
            )
        ).status_code == 422
        assert (
            await client.put("/api/v1/settings/smtp", json={**SMTP_BODY, "host": ""})
        ).status_code == 422

    async def test_ac002_requires_encryption_key(self, db_session, admin):
        os.environ.pop("SMTP_ENCRYPTION_KEY", None)
        os.environ.pop("ENCRYPTION_KEY", None)
        get_settings.cache_clear()
        client = _make_cookie_client(db_session, admin)
        resp = await client.put("/api/v1/settings/smtp", json=SMTP_BODY)
        assert resp.status_code == 409
        assert "ENCRYPTION_KEY" in resp.json()["message"]
        read = await client.get("/api/v1/settings/smtp")
        assert read.json()["encryption_key_configured"] is False

    async def test_ac001_admin_only(self, db_session, operator, encryption_key):
        client = _make_cookie_client(db_session, operator)
        assert (await client.get("/api/v1/settings/smtp")).status_code == 403
        assert (
            await client.put("/api/v1/settings/smtp", json=SMTP_BODY)
        ).status_code == 403

    async def test_ac003_test_email(self, db_session, admin, encryption_key):
        client = _make_cookie_client(db_session, admin)
        with patch(
            "app.api.endpoints.settings.send_test_email_async", new=AsyncMock()
        ) as sender:
            resp = await client.post(
                "/api/v1/settings/smtp/test", json={"to_address": "me@example.com"}
            )
        assert resp.status_code == 200
        assert resp.json() == {"sent": True, "to_address": "me@example.com"}
        sender.assert_awaited_once()

        with patch(
            "app.api.endpoints.settings.send_test_email_async",
            new=AsyncMock(side_effect=ValueError("SMTP is not configured")),
        ):
            resp = await client.post(
                "/api/v1/settings/smtp/test", json={"to_address": "me@example.com"}
            )
        assert resp.status_code == 400
        assert "not configured" in resp.json()["message"]

        with patch(
            "app.api.endpoints.settings.send_test_email_async",
            new=AsyncMock(side_effect=OSError("connect: internal host 10.0.0.5")),
        ):
            resp = await client.post(
                "/api/v1/settings/smtp/test", json={"to_address": "me@example.com"}
            )
        assert resp.status_code == 502
        assert "10.0.0.5" not in resp.text


OIDC_BODY = {
    "issuer_url": "https://id.example.com",
    "client_id": "rsync-viewer",
    "client_secret": "topsecret",
    "provider_name": "PocketID",
    "scopes": "openid email profile",
    "enabled": True,
    "hide_local_login": False,
}


class TestAC004to006Oidc:
    async def test_ac004_unconfigured_read(self, db_session, admin, encryption_key):
        client = _make_cookie_client(db_session, admin)
        body = (await client.get("/api/v1/settings/oidc")).json()
        assert body["configured"] is False
        assert body["has_client_secret"] is False
        assert body["callback_url"].endswith("/auth/oidc/callback")

    async def test_ac005_secret_required_first_time_then_optional(
        self, db_session, admin, encryption_key
    ):
        client = _make_cookie_client(db_session, admin)
        resp = await client.put(
            "/api/v1/settings/oidc", json={**OIDC_BODY, "client_secret": ""}
        )
        assert resp.status_code == 422
        assert "secret" in resp.json()["message"].lower()

        resp = await client.put("/api/v1/settings/oidc", json=OIDC_BODY)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["configured"] and body["has_client_secret"]
        assert body["enabled"] is True
        assert "topsecret" not in resp.text

        resp = await client.put(
            "/api/v1/settings/oidc",
            json={**OIDC_BODY, "client_secret": "", "provider_name": "Authelia"},
        )
        assert resp.status_code == 200
        assert resp.json()["provider_name"] == "Authelia"
        assert resp.json()["has_client_secret"] is True

    async def test_ac005_validation_and_key(self, db_session, admin, encryption_key):
        client = _make_cookie_client(db_session, admin)
        assert (
            await client.put(
                "/api/v1/settings/oidc", json={**OIDC_BODY, "issuer_url": ""}
            )
        ).status_code == 422
        os.environ.pop("SMTP_ENCRYPTION_KEY", None)
        os.environ.pop("ENCRYPTION_KEY", None)
        get_settings.cache_clear()
        assert (
            await client.put("/api/v1/settings/oidc", json=OIDC_BODY)
        ).status_code == 409

    async def test_ac006_test_discovery(self, db_session, admin, encryption_key):
        client = _make_cookie_client(db_session, admin)
        discovery = {
            "authorization_endpoint": "https://id.example.com/authorize",
            "token_endpoint": "https://id.example.com/token",
            "userinfo_endpoint": "https://id.example.com/userinfo",
            "jwks_uri": "https://id.example.com/jwks",
            "issuer": "https://id.example.com",
        }
        with patch(
            "app.api.endpoints.settings.fetch_discovery",
            new=AsyncMock(return_value=discovery),
        ):
            resp = await client.post(
                "/api/v1/settings/oidc/test-discovery",
                json={"issuer_url": "https://id.example.com"},
            )
        assert resp.status_code == 200
        assert resp.json()["endpoints"]["jwks_uri"] == "https://id.example.com/jwks"
        assert "issuer" not in resp.json()["endpoints"]

        with patch(
            "app.api.endpoints.settings.fetch_discovery",
            new=AsyncMock(side_effect=RuntimeError("timeout")),
        ):
            resp = await client.post(
                "/api/v1/settings/oidc/test-discovery",
                json={"issuer_url": "https://id.example.com"},
            )
        assert resp.status_code == 400
        assert "timeout" in resp.json()["message"]


class TestAC007Synthetic:
    async def test_ac007_read_and_write(self, db_session, admin):
        client = _make_cookie_client(db_session, admin)
        body = (await client.get("/api/v1/settings/synthetic")).json()
        assert set(body) >= {
            "enabled",
            "interval_seconds",
            "last_status",
            "last_check_at",
            "last_latency_ms",
            "last_error",
        }

        with (
            patch(
                "app.api.endpoints.settings.start_synthetic_monitoring", new=AsyncMock()
            ) as start,
            patch(
                "app.api.endpoints.settings.stop_synthetic_monitoring", new=AsyncMock()
            ) as stop,
        ):
            resp = await client.put(
                "/api/v1/settings/synthetic",
                json={"enabled": True, "interval_seconds": 10},
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["enabled"] is True
            assert resp.json()["interval_seconds"] == 30  # clamped
            start.assert_awaited_once()

            resp = await client.put(
                "/api/v1/settings/synthetic",
                json={"enabled": False, "interval_seconds": 120},
            )
            assert resp.json()["enabled"] is False
            stop.assert_awaited_once()

        row = db_session.exec(select(SyntheticCheckConfig)).one()
        assert row.enabled is False and row.interval_seconds == 120

    async def test_ac007_admin_only(self, db_session, operator):
        client = _make_cookie_client(db_session, operator)
        assert (await client.get("/api/v1/settings/synthetic")).status_code == 403


class TestAC008MonitoringSetup:
    async def test_ac008_generates_snippet_and_key(self, db_session, admin):
        client = _make_cookie_client(db_session, admin)
        resp = await client.post(
            "/api/v1/settings/monitoring-setup",
            json={"source_name": "NAS Backup", "rsync_source": "bob@nas.local:/data"},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["source_name"] == "nas-backup"
        assert body["key_name"] == "rsync-client-nas-backup"
        assert body["api_key"].startswith("rsv_")
        assert body["api_key"] in body["snippet"]
        assert "REMOTE_HOST=nas.local" in body["snippet"]
        assert "CRON_SCHEDULE=0 */6 * * *" in body["snippet"]

        key = db_session.exec(
            select(ApiKey).where(ApiKey.name == "rsync-client-nas-backup")
        ).one()
        assert key.user_id == admin.id and key.is_active

        # second run for the same source gets a unique key name
        resp = await client.post(
            "/api/v1/settings/monitoring-setup",
            json={"source_name": "nas-backup", "rsync_source": "bob@nas.local:/data"},
        )
        assert resp.json()["key_name"] == "rsync-client-nas-backup-2"

    async def test_ac008_validation(self, db_session, admin):
        client = _make_cookie_client(db_session, admin)
        resp = await client.post(
            "/api/v1/settings/monitoring-setup",
            json={"source_name": "x", "rsync_source": "not-a-source"},
        )
        assert resp.status_code == 422
        assert "user@host:/path" in resp.text


class TestAC009Changelog:
    async def test_ac009_changelog_for_any_user(self, db_session, viewer):
        client = _make_bearer_client(db_session, viewer)
        resp = await client.get("/api/v1/changelog")
        assert resp.status_code == 200
        body = resp.json()
        assert body["app_version"]
        assert 1 <= len(body["versions"]) <= 5
        assert all(v["version"] != "Unreleased" for v in body["versions"])
        assert body["has_more"] in (True, False)
        first = body["versions"][0]
        assert set(first) >= {"version", "date", "sections"}

        everything = (await client.get("/api/v1/changelog?all=true")).json()
        assert len(everything["versions"]) >= len(body["versions"])
        assert everything["has_more"] is False

    async def test_ac009_requires_auth(self, db_session):
        assert (
            await _make_unauth_client(db_session).get("/api/v1/changelog")
        ).status_code == 401
