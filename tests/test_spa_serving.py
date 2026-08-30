"""Tests for specs/insight-ui.md AC-022 — serving the SPA from FastAPI."""

import os

import pytest

from app.config import get_settings


@pytest.fixture
def spa_dist(tmp_path):
    """Point SPA_DIST_DIR at a temp build containing a stub index.html."""
    dist = tmp_path / "app"
    dist.mkdir()
    (dist / "index.html").write_text(
        '<!doctype html><head></head><div id="root"></div>'
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


class TestAC022SpaServing:
    @pytest.mark.parametrize("path", ["/app", "/app/media", "/app/transfers?source=x"])
    async def test_ac022_serves_index_for_spa_routes(self, spa_dist, client, path):
        resp = await client.get(path)
        assert resp.status_code == 200
        assert 'id="root"' in resp.text
        assert resp.headers["cache-control"] == "no-store"

    async def test_ac022_missing_build_returns_helpful_404(self, spa_dist, client):
        (spa_dist / "index.html").unlink()
        resp = await client.get("/app")
        assert resp.status_code == 404
        assert "frontend build" in resp.json()["message"].lower()

    async def test_ac022_unauthenticated_redirects_to_login(
        self, spa_dist, unauth_client
    ):
        resp = await unauth_client.get("/app/media", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/login?return_url=/app/media"


class TestFooterVersionInjection:
    """specs/footer-version.md AC-001/AC-003."""

    @pytest.mark.anyio
    async def test_ac001_shell_carries_app_version(self, spa_dist, client):
        response = await client.get("/app")
        assert response.status_code == 200
        assert 'window.__APP_VERSION__ = "' in response.text

    @pytest.mark.anyio
    async def test_ac003_login_page_has_version_footer(self, client):
        response = await client.get("/login")
        assert response.status_code == 200
        assert 'class="app-footer"' in response.text
        assert 'href="/app/settings/changelog"' in response.text
        # the version itself is the link text
        assert '/app/settings/changelog" style="color:inherit;">v' in response.text
