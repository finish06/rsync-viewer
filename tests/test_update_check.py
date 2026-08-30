"""Tests for specs/cicd-release.md AC-006/AC-007 — update awareness."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.services import update_check
from app.services.update_check import (
    UpdateStatus,
    compare_versions,
    get_update_status,
)
from app.utils import utc_now


@pytest.fixture(autouse=True)
def _clear_cache():
    update_check.clear_cache()
    yield
    update_check.clear_cache()


class TestAC007SemverCompare:
    @pytest.mark.parametrize(
        "current,latest,newer",
        [
            ("2.17.0", "2.18.0", True),
            ("2.9.0", "2.10.0", True),  # numeric, not lexicographic
            ("v2.17.0", "v2.17.1", True),
            ("2.17.0", "2.17.0", False),
            ("2.18.0", "2.17.5", False),  # local build ahead
            ("dev", "2.18.0", False),  # dev builds never nag
            ("2.17.0", "not-a-version", False),
        ],
    )
    def test_ac007_compare(self, current, latest, newer):
        assert compare_versions(current, latest) is newer


class TestAC006UpdateStatus:
    def _release(self, tag="v2.18.0"):
        return {
            "tag_name": tag,
            "html_url": f"https://github.com/finish06/rsync-viewer/releases/tag/{tag}",
            "published_at": "2026-08-30T12:00:00Z",
        }

    @pytest.mark.anyio
    async def test_ac006_reports_newer_release(self):
        with patch(
            "app.services.update_check._fetch_latest_release",
            new_callable=AsyncMock,
            return_value=self._release(),
        ):
            status = await get_update_status(current="2.17.0")
        assert isinstance(status, UpdateStatus)
        assert status.latest == "2.18.0"
        assert status.update_available is True
        assert status.release_url.endswith("/v2.18.0")

    @pytest.mark.anyio
    async def test_ac006_cache_prevents_repeat_fetches(self):
        with patch(
            "app.services.update_check._fetch_latest_release",
            new_callable=AsyncMock,
            return_value=self._release(),
        ) as fetch:
            await get_update_status(current="2.17.0")
            await get_update_status(current="2.17.0")
        assert fetch.call_count == 1

    @pytest.mark.anyio
    async def test_ac006_expired_cache_refetches(self):
        with patch(
            "app.services.update_check._fetch_latest_release",
            new_callable=AsyncMock,
            return_value=self._release(),
        ) as fetch:
            await get_update_status(current="2.17.0")
            update_check._cache["checked_at"] = utc_now() - timedelta(days=2)
            await get_update_status(current="2.17.0")
        assert fetch.call_count == 2

    @pytest.mark.anyio
    async def test_ac006_fetch_failure_degrades_gracefully(self):
        with patch(
            "app.services.update_check._fetch_latest_release",
            new_callable=AsyncMock,
            side_effect=RuntimeError("github down"),
        ):
            status = await get_update_status(current="2.17.0")
        assert status.latest is None
        assert status.update_available is False

    @pytest.mark.anyio
    async def test_ac006_disabled_never_calls_out(self, monkeypatch):
        from app.config import get_settings

        monkeypatch.setenv("UPDATE_CHECK_ENABLED", "false")
        get_settings.cache_clear()
        try:
            with patch(
                "app.services.update_check._fetch_latest_release",
                new_callable=AsyncMock,
            ) as fetch:
                status = await get_update_status(current="2.17.0")
            assert fetch.call_count == 0
            assert status.update_available is False
        finally:
            get_settings.cache_clear()


class TestAC006Endpoint:
    @pytest.mark.anyio
    async def test_ac006_endpoint_shape(self, client):
        from types import SimpleNamespace

        # The test app runs as version "dev"; pretend it is a real build.
        with (
            patch(
                "app.api.endpoints.version_updates.get_settings",
                return_value=SimpleNamespace(app_version="2.17.0"),
            ),
            patch(
                "app.services.update_check._fetch_latest_release",
                new_callable=AsyncMock,
                return_value={
                    "tag_name": "v99.0.0",
                    "html_url": "https://github.com/finish06/rsync-viewer/releases/tag/v99.0.0",
                    "published_at": "2026-08-30T12:00:00Z",
                },
            ),
        ):
            response = await client.get("/api/v1/version/updates")
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "current",
            "latest",
            "update_available",
            "release_url",
            "published_at",
            "checked_at",
        }
        assert body["current"] == "2.17.0"
        assert body["latest"] == "99.0.0"
        assert body["update_available"] is True

    @pytest.mark.anyio
    async def test_ac006_endpoint_requires_auth(self, unauth_client):
        response = await unauth_client.get("/api/v1/version/updates")
        assert response.status_code in (401, 403)


class TestAppVersionNormalisation:
    """The container is built with the tag (v2.18.0); everything downstream
    expects the bare version — normalise once in Settings."""

    def test_leading_v_is_stripped(self, monkeypatch):
        from app.config import Settings, get_settings

        monkeypatch.setenv("APP_VERSION", "v2.18.0")
        get_settings.cache_clear()
        try:
            assert Settings().app_version == "2.18.0"
        finally:
            get_settings.cache_clear()

    def test_plain_and_dev_versions_unchanged(self):
        from app.config import Settings

        assert Settings(app_version="2.18.0").app_version == "2.18.0"
        assert Settings(app_version="dev").app_version == "dev"
