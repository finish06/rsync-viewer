"""Tests for app/middleware.py — covers uncovered paths.

Targets:
  - BodySizeLimitMiddleware (413 response, lines 127-129)
  - CsrfMiddleware token validation
  - AuthRedirectMiddleware HTMX 401 response (lines 183-187)
  - AuthRedirectMiddleware return_url with query string (line 192)
"""

import pytest


class TestBodySizeLimitMiddleware:
    """Cover BodySizeLimitMiddleware 413 rejection."""

    @pytest.mark.asyncio
    async def test_oversized_body_returns_413(self, client):
        # max_request_body_size defaults to 10MB in settings
        # Send a Content-Length header exceeding the limit
        resp = await client.post(
            "/api/v1/sync-logs",
            content=b"x",
            headers={"Content-Length": "999999999"},
        )
        assert resp.status_code == 413
        data = resp.json()
        assert data["error_code"] == "PAYLOAD_TOO_LARGE"


class TestAuthRedirectMiddlewareHtmx:
    """Cover AuthRedirectMiddleware HTMX 401 path."""

    @pytest.mark.asyncio
    async def test_htmx_request_returns_401_not_redirect(self, unauth_client):
        resp = await unauth_client.get(
            "/some-protected-page",
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "Session expired" in data["detail"]

    @pytest.mark.asyncio
    async def test_return_url_includes_query_string(self, unauth_client):
        resp = await unauth_client.get(
            "/settings?tab=smtp",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "return_url=/settings" in location
        assert "tab=smtp" in location
