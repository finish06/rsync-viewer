"""Tests for specs/settings-ui.md AC-010 — CSRF on cookie-authenticated API mutations."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app.csrf import generate_csrf_token
from app.main import app
from app.models.user import User
from app.services.auth import ROLE_OPERATOR, hash_password
from tests.test_rbac import _make_cookie_client, _setup_overrides, create_access_token

WEBHOOK = {"name": "csrf-hook", "url": "https://example.com/hook"}


@pytest.fixture
def operator(db_session: Session) -> User:
    user = User(
        username="csrf_operator",
        email="csrf_operator@test.com",
        password_hash=hash_password("OperPass1!"),
        role=ROLE_OPERATOR,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _cookie_client_without_csrf_header(db_session, user: User) -> AsyncClient:
    _setup_overrides(db_session)
    token = create_access_token(user.id, user.username, user.role)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"access_token": token, "csrf_token": generate_csrf_token()},
    )


class TestAC010CsrfOnApi:
    async def test_ac010_cookie_mutation_without_header_is_rejected(
        self, db_session, operator
    ):
        client = _cookie_client_without_csrf_header(db_session, operator)
        resp = await client.post("/api/v1/webhooks", json=WEBHOOK)
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "CSRF_VALIDATION_FAILED"

    async def test_ac010_cookie_mutation_with_mismatched_header_is_rejected(
        self, db_session, operator
    ):
        client = _cookie_client_without_csrf_header(db_session, operator)
        resp = await client.post(
            "/api/v1/webhooks", json=WEBHOOK, headers={"X-CSRF-Token": "wrong"}
        )
        assert resp.status_code == 403

    async def test_ac010_cookie_mutation_with_valid_header_succeeds(
        self, db_session, operator
    ):
        client = _make_cookie_client(db_session, operator)  # sets matching header
        resp = await client.post("/api/v1/webhooks", json=WEBHOOK)
        assert resp.status_code == 201

    async def test_ac010_api_key_auth_is_exempt(self, client):
        # conftest client sends X-API-Key (dev key) — no CSRF required
        resp = await client.post(
            "/api/v1/webhooks",
            json=WEBHOOK,
            headers={"X-CSRF-Token": ""},
        )
        assert resp.status_code == 201

    async def test_ac010_bearer_auth_is_exempt(self, db_session, operator):
        _setup_overrides(db_session)
        token = create_access_token(operator.id, operator.username, operator.role)
        client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.post("/api/v1/webhooks", json=WEBHOOK)
        assert resp.status_code == 201

    async def test_ac010_reads_never_require_csrf(self, db_session, operator):
        client = _cookie_client_without_csrf_header(db_session, operator)
        assert (await client.get("/api/v1/webhooks")).status_code == 200

    async def test_ac010_spa_shell_sets_csrf_cookie_when_missing(
        self, db_session, operator
    ):
        _setup_overrides(db_session)
        token = create_access_token(operator.id, operator.username, operator.role)
        client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={"access_token": token},
        )
        resp = await client.get("/app")
        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "")
        assert "csrf_token=" in set_cookie
        assert "HttpOnly" not in set_cookie  # the SPA must be able to read it
