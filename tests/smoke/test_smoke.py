"""Smoke tests for production deployment verification.

These tests run against a live instance (no DB fixtures, no test client).
Configure target via SMOKE_TEST_URL environment variable.

Usage:
    pytest tests/smoke/ -m smoke
    SMOKE_TEST_URL=https://rsync.example.com pytest tests/smoke/ -m smoke
"""

import os

import httpx
import pytest

SMOKE_TEST_URL = os.environ.get("SMOKE_TEST_URL", "http://localhost:8000")


@pytest.fixture
def client() -> httpx.Client:
    return httpx.Client(base_url=SMOKE_TEST_URL, timeout=10.0)


@pytest.mark.smoke
def test_health_endpoint(client: httpx.Client) -> None:
    """GET /health returns 200 with status: ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.smoke
def test_metrics_endpoint(client: httpx.Client) -> None:
    """GET /metrics returns 200 with Prometheus text format."""
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    # Prometheus exposition format contains TYPE and HELP lines
    assert "# TYPE" in body or "# HELP" in body


@pytest.mark.smoke
def test_login_page_accessible(client: httpx.Client) -> None:
    """GET /login returns 200."""
    response = client.get("/login", follow_redirects=True)
    assert response.status_code == 200


@pytest.mark.smoke
def test_api_docs_accessible(client: httpx.Client) -> None:
    """GET /docs returns 200 (FastAPI Swagger UI)."""
    response = client.get("/docs")
    assert response.status_code == 200


@pytest.mark.smoke
def test_security_headers_present(client: httpx.Client) -> None:
    """Responses include required security headers."""
    response = client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"


@pytest.mark.smoke
def test_api_requires_auth(client: httpx.Client) -> None:
    """POST /api/v1/sync-logs without API key returns 401 or 403."""
    response = client.post(
        "/api/v1/sync-logs",
        json={"source_name": "smoke-test", "raw_content": "test"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.smoke
def test_rate_limit_headers(client: httpx.Client) -> None:
    """API responses include X-RateLimit-* headers from slowapi."""
    response = client.get("/health")
    # slowapi injects rate limit headers on limited endpoints
    # /health may not be rate-limited, so check a page that is
    page_response = client.get("/login", follow_redirects=True)
    has_rate_headers = (
        "X-RateLimit-Limit" in response.headers
        or "X-RateLimit-Limit" in page_response.headers
    )
    assert has_rate_headers, "No X-RateLimit-* headers found on any endpoint"
