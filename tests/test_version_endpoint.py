"""Tests for /version endpoint (specs/version-endpoint.md)."""

import time


class TestVersionEndpoint:
    """AC-001 through AC-012: /version endpoint."""

    async def test_ac001_returns_all_fields(self, client):
        """GET /version returns all required fields."""
        response = await client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "python_version" in data
        assert "os" in data
        assert "arch" in data
        assert "hostname" in data
        assert "uptime_seconds" in data
        assert "start_time" in data

    async def test_ac002_version_from_settings(self, client):
        """Version comes from APP_VERSION setting."""
        response = await client.get("/version")
        data = response.json()
        # In test mode, app_version defaults to "dev" or whatever test settings provide
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    async def test_ac003_python_version_populated(self, client):
        """python_version is a real Python version string."""
        response = await client.get("/version")
        data = response.json()
        assert "." in data["python_version"]  # e.g. "3.11.11"

    async def test_ac004_os_arch_populated(self, client):
        """os and arch are non-empty strings."""
        response = await client.get("/version")
        data = response.json()
        assert len(data["os"]) > 0
        assert len(data["arch"]) > 0

    async def test_ac005_hostname_populated(self, client):
        """hostname is a non-empty string."""
        response = await client.get("/version")
        data = response.json()
        assert len(data["hostname"]) > 0

    async def test_ac006_uptime_increases(self, client):
        """uptime_seconds increases between requests."""
        r1 = await client.get("/version")
        t1 = r1.json()["uptime_seconds"]
        time.sleep(1)
        r2 = await client.get("/version")
        t2 = r2.json()["uptime_seconds"]
        assert t2 > t1

    async def test_ac006_start_time_is_iso8601(self, client):
        """start_time is a valid ISO 8601 string."""
        from datetime import datetime

        response = await client.get("/version")
        data = response.json()
        # Should parse without error
        dt = datetime.fromisoformat(data["start_time"])
        assert dt.year >= 2026

    async def test_ac008_unauthenticated_access(self, unauth_client):
        """GET /version works without authentication."""
        response = await unauth_client.get("/version")
        assert response.status_code == 200
        assert "version" in response.json()

    async def test_ac010_health_includes_version(self, client):
        """GET /health response includes version field."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data

    async def test_ac007_build_info_metric(self, client):
        """Prometheus metrics include rsync_viewer_build_info gauge."""
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "rsync_viewer_build_info" in response.text
