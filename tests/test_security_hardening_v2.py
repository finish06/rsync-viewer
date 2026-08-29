"""Tests for specs/security-hardening-v2.md (Phase 0 hotfixes).

Covers:
  AC-001: Analytics API requires authentication (viewer+)
  AC-009: Monitors/failures accept API key or JWT with role checks
  AC-010: Webhook read paths require operator (secrets hidden from viewers)
"""

from uuid import uuid4

import pytest
from sqlmodel import Session

from app.api.deps import hash_api_key
from app.models.sync_log import ApiKey
from app.models.user import User
from app.models.webhook import WebhookEndpoint
from app.services.auth import ROLE_VIEWER, hash_password
from tests.test_rbac import (
    _make_bearer_client,
    _make_unauth_client,
    _setup_overrides,
)

VIEWER_KEY_RAW = "rsv_viewerkey_0123456789abcdef"


@pytest.fixture
def viewer_user(db_session: Session) -> User:
    user = User(
        username="v2_viewer",
        email="v2_viewer@test.com",
        password_hash=hash_password("ViewPass1!"),
        role=ROLE_VIEWER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def viewer_api_key(db_session: Session, viewer_user: User) -> str:
    """A per-user API key explicitly scoped to the viewer role."""
    key = ApiKey(
        id=uuid4(),
        key_hash=hash_api_key(VIEWER_KEY_RAW),
        key_prefix=VIEWER_KEY_RAW[:8],
        name="viewer key",
        is_active=True,
        user_id=viewer_user.id,
        role_override=ROLE_VIEWER,
    )
    db_session.add(key)
    db_session.flush()
    return VIEWER_KEY_RAW


@pytest.fixture
def webhook(db_session: Session) -> WebhookEndpoint:
    wh = WebhookEndpoint(
        id=uuid4(),
        name="Secret Hook",
        url="https://hooks.example.com/services/T000/B000/SECRET-TOKEN",
        headers={"Authorization": "Bearer hook-secret"},
        webhook_type="generic",
        enabled=True,
    )
    db_session.add(wh)
    db_session.commit()
    db_session.refresh(wh)
    return wh


class TestAC001AnalyticsRequiresAuth:
    """AC-001: analytics endpoints return 401 without credentials."""

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/analytics/summary?period=daily&start=2026-01-01&end=2026-01-02",
            "/api/v1/analytics/sources",
            "/api/v1/analytics/export?format=json",
        ],
    )
    async def test_ac001_analytics_requires_auth(self, db_session, path):
        client = _make_unauth_client(db_session)
        resp = await client.get(path)
        assert resp.status_code == 401

    async def test_ac001_viewer_jwt_can_read_summary(self, db_session, viewer_user):
        client = _make_bearer_client(db_session, viewer_user)
        resp = await client.get(
            "/api/v1/analytics/summary?period=daily&start=2026-01-01&end=2026-01-02"
        )
        assert resp.status_code == 200


class TestAC009MonitorsFailuresRoles:
    """AC-009: monitors/failures accept JWT; viewer read, operator write."""

    async def test_ac009_jwt_can_list_monitors(self, db_session, viewer_user):
        client = _make_bearer_client(db_session, viewer_user)
        resp = await client.get("/api/v1/monitors")
        assert resp.status_code == 200

    async def test_ac009_jwt_can_list_failures(self, db_session, viewer_user):
        client = _make_bearer_client(db_session, viewer_user)
        resp = await client.get("/api/v1/failures")
        assert resp.status_code == 200

    async def test_ac009_viewer_jwt_cannot_create_monitor(
        self, db_session, viewer_user
    ):
        client = _make_bearer_client(db_session, viewer_user)
        resp = await client.post(
            "/api/v1/monitors",
            json={"source_name": "backup", "expected_interval_hours": 24},
        )
        assert resp.status_code == 403

    async def test_ac009_viewer_key_cannot_create_monitor(
        self, db_session, viewer_api_key
    ):
        client = _make_unauth_client(db_session)
        resp = await client.post(
            "/api/v1/monitors",
            json={"source_name": "backup", "expected_interval_hours": 24},
            headers={"X-API-Key": viewer_api_key},
        )
        assert resp.status_code == 403

    async def test_ac009_viewer_key_can_list_monitors(self, db_session, viewer_api_key):
        client = _make_unauth_client(db_session)
        resp = await client.get(
            "/api/v1/monitors", headers={"X-API-Key": viewer_api_key}
        )
        assert resp.status_code == 200

    async def test_ac009_monitors_require_auth(self, db_session):
        _setup_overrides(db_session)
        client = _make_unauth_client(db_session)
        resp = await client.get("/api/v1/monitors")
        assert resp.status_code == 401


class TestAC010WebhookReadsRequireOperator:
    """AC-010: viewers cannot list or open webhooks (URLs/headers are secrets)."""

    async def test_ac010_viewer_cannot_list_webhooks_api(
        self, db_session, viewer_user, webhook
    ):
        client = _make_bearer_client(db_session, viewer_user)
        resp = await client.get("/api/v1/webhooks")
        assert resp.status_code == 403
        assert "SECRET-TOKEN" not in resp.text
