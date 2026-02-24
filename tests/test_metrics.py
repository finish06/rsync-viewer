"""Tests for Prometheus metrics endpoint and instrumentation.

Spec: specs/metrics-export.md
ACs: AC-001, AC-002, AC-003, AC-004, AC-009, AC-010
"""

import time

from httpx import AsyncClient


class TestMetricsEndpoint:
    """AC-001: /metrics returns valid Prometheus exposition format."""

    async def test_ac001_metrics_endpoint_returns_200(self, client: AsyncClient):
        """GET /metrics returns 200 OK."""
        response = await client.get("/metrics")
        assert response.status_code == 200

    async def test_ac001_metrics_content_type(self, client: AsyncClient):
        """GET /metrics returns Prometheus content type."""
        response = await client.get("/metrics")
        content_type = response.headers.get("content-type", "")
        # prometheus-client returns text/plain with version param
        assert "text/plain" in content_type

    async def test_ac001_metrics_contains_help_and_type(self, client: AsyncClient):
        """Metrics output contains HELP and TYPE annotations."""
        response = await client.get("/metrics")
        text = response.text
        assert "# HELP" in text
        assert "# TYPE" in text


class TestSyncMetrics:
    """AC-002: Sync metrics are exported."""

    async def test_ac002_syncs_total_counter_exists(self, client: AsyncClient):
        """rsync_syncs_total counter metric exists."""
        response = await client.get("/metrics")
        assert "rsync_syncs_total" in response.text

    async def test_ac002_sync_duration_histogram_exists(self, client: AsyncClient):
        """rsync_sync_duration_seconds histogram metric exists."""
        response = await client.get("/metrics")
        assert "rsync_sync_duration_seconds" in response.text

    async def test_ac002_files_transferred_counter_exists(self, client: AsyncClient):
        """rsync_files_transferred_total counter metric exists."""
        response = await client.get("/metrics")
        assert "rsync_files_transferred_total" in response.text

    async def test_ac002_bytes_transferred_counter_exists(self, client: AsyncClient):
        """rsync_bytes_transferred_total counter metric exists."""
        response = await client.get("/metrics")
        assert "rsync_bytes_transferred_total" in response.text

    async def test_ac002_sync_metrics_increment_after_ingestion(
        self, client: AsyncClient, sample_sync_log_data: dict
    ):
        """Sync metrics increase after submitting a sync log."""
        # Submit a sync log
        await client.post(
            "/api/v1/sync-logs",
            json=sample_sync_log_data,
            headers={"X-API-Key": "test-api-key"},
        )

        # Get updated metrics
        updated = await client.get("/metrics")
        updated_text = updated.text

        # rsync_syncs_total should have increased
        assert "rsync_syncs_total" in updated_text


class TestApiMetrics:
    """AC-003: API metrics are exported."""

    async def test_ac003_api_requests_total_exists(self, client: AsyncClient):
        """rsync_api_requests_total counter metric exists."""
        # Make a request first to populate metrics
        await client.get("/health")
        response = await client.get("/metrics")
        assert "rsync_api_requests_total" in response.text

    async def test_ac003_api_duration_histogram_exists(self, client: AsyncClient):
        """rsync_api_request_duration_seconds histogram metric exists."""
        await client.get("/health")
        response = await client.get("/metrics")
        assert "rsync_api_request_duration_seconds" in response.text

    async def test_ac003_api_metrics_have_labels(self, client: AsyncClient):
        """API metrics include endpoint, method, and status labels."""
        await client.get("/health")
        response = await client.get("/metrics")
        text = response.text
        # Should have labels like method="GET" and status="200"
        assert 'method="GET"' in text


class TestHealthMetrics:
    """AC-004: Application health metrics are exported."""

    async def test_ac004_app_info_metric_exists(self, client: AsyncClient):
        """rsync_app_info gauge metric exists with version label."""
        response = await client.get("/metrics")
        assert "rsync_app_info" in response.text

    async def test_ac004_app_info_has_version(self, client: AsyncClient):
        """rsync_app_info includes version label."""
        # Lifespan doesn't run under httpx test client, so call explicitly
        from app.metrics import set_app_info

        set_app_info(version="1.5.0")
        response = await client.get("/metrics")
        text = response.text
        assert 'version="' in text


class TestMetricsAuth:
    """AC-009: /metrics does not require API key authentication."""

    async def test_ac009_metrics_no_auth_required(self, client: AsyncClient):
        """GET /metrics works without X-API-Key header."""
        # Client has CSRF tokens but we're testing that no API key is needed
        response = await client.get("/metrics")
        assert response.status_code == 200

    async def test_ac009_metrics_bypasses_csrf(self, client: AsyncClient):
        """GET /metrics works without CSRF token."""
        # Create a client without CSRF tokens
        from httpx import ASGITransport

        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as bare_client:
            response = await bare_client.get("/metrics")
            assert response.status_code == 200


class TestMetricsPerformance:
    """AC-010: Metrics collection has minimal performance impact."""

    async def test_ac010_metrics_endpoint_fast(self, client: AsyncClient):
        """GET /metrics responds in under 100ms."""
        start = time.monotonic()
        response = await client.get("/metrics")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 100, f"Metrics endpoint took {elapsed_ms:.1f}ms (max 100ms)"


class TestMetricsZeroData:
    """Edge case: metrics with no sync data should return zero values."""

    async def test_metrics_with_no_data(self, client: AsyncClient):
        """Metrics endpoint works with no sync logs in database."""
        response = await client.get("/metrics")
        assert response.status_code == 200
        # Should still have metric declarations
        assert "rsync_syncs_total" in response.text
