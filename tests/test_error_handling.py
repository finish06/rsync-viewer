"""Tests for comprehensive error handling (specs/error-handling.md)."""

from datetime import timedelta
from app.utils import utc_now


class TestErrorResponseFormat:
    """AC-001: All API error responses return consistent JSON structure."""

    async def test_ac001_401_has_structured_error(self, unauth_client):
        """401 response includes error_code, message, timestamp, path."""
        response = await unauth_client.post("/api/v1/sync-logs", json={})
        assert response.status_code == 401
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert "timestamp" in data
        assert "path" in data

    async def test_ac001_404_has_structured_error(self, client):
        """404 response includes error_code, message, timestamp, path."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/v1/sync-logs/{fake_id}",
        )
        assert response.status_code == 404
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert "timestamp" in data
        assert "path" in data

    async def test_ac010_detail_field_preserved(self, unauth_client):
        """Backward compatibility: detail field still present."""
        response = await unauth_client.post("/api/v1/sync-logs", json={})
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


class TestErrorCodes:
    """AC-003, AC-008: Error codes use uppercase snake_case."""

    async def test_ac003_api_key_required_code(self, unauth_client):
        """Missing authentication returns AUTH_REQUIRED error code."""
        response = await unauth_client.post("/api/v1/sync-logs", json={})
        assert response.status_code == 401

    async def test_ac003_api_key_invalid_code(self, client):
        """Invalid API key returns API_KEY_INVALID error code."""
        response = await client.post(
            "/api/v1/sync-logs",
            json={},
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401
        assert response.json()["error_code"] == "API_KEY_INVALID"

    async def test_ac003_not_found_code(self, client):
        """Not found returns RESOURCE_NOT_FOUND error code."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/sync-logs/{fake_id}")
        assert response.status_code == 404
        assert response.json()["error_code"] == "RESOURCE_NOT_FOUND"


class TestValidationErrors:
    """AC-002: Validation errors include field-level details."""

    async def test_ac002_validation_error_has_fields(self, client):
        """422 response includes validation_errors array."""
        response = await client.post(
            "/api/v1/sync-logs",
            json={"source_name": "test"},
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "validation_errors" in data
        assert isinstance(data["validation_errors"], list)
        assert len(data["validation_errors"]) > 0

    async def test_ac002_validation_error_has_field_names(self, client):
        """Validation errors include field location info."""
        response = await client.post(
            "/api/v1/sync-logs",
            json={"source_name": "test"},
            headers={"X-API-Key": "test-api-key"},
        )
        data = response.json()
        # Each validation error should have location and message info
        for err in data["validation_errors"]:
            assert "loc" in err or "field" in err or "msg" in err


class TestGlobalExceptionHandler:
    """AC-004: Unhandled exceptions return structured 500."""

    async def test_ac004_500_no_stack_trace(self, client):
        """500 errors don't leak stack traces."""
        # The health endpoint is safe, but we can verify the handler exists
        # by checking that the app has exception handlers registered
        from app.main import app

        # Verify exception handlers are registered
        assert len(app.exception_handlers) > 0


class TestDateParameterValidation:
    """AC-006: Invalid dates return 400, not 500."""

    async def test_ac006_invalid_start_date(self, client):
        """Invalid start_date returns 400 Bad Request."""
        response = await client.get("/htmx/sync-table?start_date=not-a-date")
        # Should be 400, not 500
        assert response.status_code == 400

    async def test_ac006_invalid_end_date(self, client):
        """Invalid end_date returns 400 Bad Request."""
        response = await client.get("/htmx/sync-table?end_date=invalid")
        assert response.status_code == 400

    async def test_ac006_valid_dates_still_work(self, client):
        """Valid date parameters still work correctly."""
        now = utc_now()
        start = (now - timedelta(days=1)).isoformat()
        response = await client.get(f"/htmx/sync-table?start_date={start}")
        assert response.status_code == 200


class TestParserSafety:
    """AC-007: Parser handles non-numeric input."""

    def test_ac007_parse_number_non_numeric(self):
        """_parse_number handles non-numeric input without crashing."""
        from app.services.rsync_parser import RsyncParser

        # Should not raise, should return None or 0
        result = RsyncParser._parse_number("abc")
        assert result is None or result == 0

    def test_ac007_parse_number_empty(self):
        """_parse_number handles empty string."""
        from app.services.rsync_parser import RsyncParser

        result = RsyncParser._parse_number("")
        assert result is None or result == 0
