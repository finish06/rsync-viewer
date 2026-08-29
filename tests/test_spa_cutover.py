"""Tests for specs/insight-ui.md AC-024 — `/` serves the SPA after cut-over."""

import json
import os

import pytest

from app.config import get_settings


@pytest.fixture
def spa_dist(tmp_path):
    dist = tmp_path / "app"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<!doctype html><html><head><title>x</title></head>"
        '<body><div id="root"></div></body></html>'
    )
    previous = os.environ.get("SPA_DIST_DIR")
    os.environ["SPA_DIST_DIR"] = str(dist)
    get_settings.cache_clear()
    try:
        yield dist
    finally:
        if previous is None:
            os.environ.pop("SPA_DIST_DIR", None)
        else:
            os.environ["SPA_DIST_DIR"] = previous
        get_settings.cache_clear()


def _injected_user(html: str) -> dict:
    marker = "window.__USER__ = "
    start = html.index(marker) + len(marker)
    end = html.index(";", start)
    return json.loads(html[start:end])


class TestAC024RootServesSpa:
    async def test_ac024_root_serves_spa_with_user_context(self, spa_dist, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert 'id="root"' in resp.text
        head = resp.text.split("</head>")[0]
        user = _injected_user(head)
        assert user["username"] == "test-operator"
        assert user["role"] == "operator"
        assert "window.__USER_THEME__" in head
        assert resp.headers["cache-control"] == "no-store"

    async def test_ac024_theme_preference_injected_before_body(
        self, spa_dist, client, db_session
    ):
        from sqlmodel import select

        from app.models.user import User

        user = db_session.exec(
            select(User).where(User.username == "test-operator")
        ).one()
        user.preferences = {"theme": "dark"}
        db_session.add(user)
        db_session.flush()

        resp = await client.get("/")
        head = resp.text.split("</head>")[0]
        assert 'window.__USER_THEME__ = "dark"' in head
        assert _injected_user(head)["theme"] == "dark"

    async def test_ac024_injection_is_html_safe(self, spa_dist, client, db_session):
        from sqlmodel import select

        from app.models.user import User

        user = db_session.exec(
            select(User).where(User.username == "test-operator")
        ).one()
        user.preferences = {"theme": "</script><script>alert(1)</script>"}
        db_session.add(user)
        db_session.flush()

        resp = await client.get("/")
        assert "</script><script>alert(1)" not in resp.text
        assert "<\\/script>" in resp.text

    async def test_ac024_root_redirects_unauthenticated(self, spa_dist, unauth_client):
        resp = await unauth_client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"].startswith("/login")

    @pytest.mark.parametrize(
        "path,target",
        [
            ("/analytics", "/app/trends"),
            ("/?tab=analytics", "/app/trends"),
            ("/?tab=notifications", "/notifications"),
        ],
    )
    async def test_ac024_legacy_links_redirect(self, spa_dist, client, path, target):
        resp = await client.get(path, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == target

    async def test_ac024_legacy_partials_are_gone(self, spa_dist, client):
        for path in (
            "/htmx/sync-table",
            "/htmx/analytics",
            "/htmx/charts",
            "/htmx/sync-detail/00000000-0000-4000-8000-000000000000",
        ):
            assert (await client.get(path)).status_code == 404, path


class TestNotificationsPage:
    async def test_notifications_page_is_server_rendered(self, client):
        resp = await client.get("/notifications")
        assert resp.status_code == 200
        assert 'hx-get="/htmx/notifications' in resp.text
        assert "Notifications" in resp.text
        assert 'href="/"' in resp.text  # back to the dashboard

    async def test_notifications_partial_still_works(self, client):
        assert (await client.get("/htmx/notifications")).status_code == 200
