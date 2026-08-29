"""Tests for HTMX handler endpoints and dashboard pages."""

from datetime import timedelta


class TestHealthEndpoint:
    """Test GET /health endpoint"""

    async def test_health_returns_ok(self, client):
        """Test health endpoint returns ok status"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "synthetic_check" in data


class TestTemplateFilters:
    """Test custom template filters"""

    def test_format_bytes_none(self):
        """Test format_bytes with None returns dash"""
        from app.main import format_bytes

        assert format_bytes(None) == "-"

    def test_format_bytes_small(self):
        """Test format_bytes with small values"""
        from app.main import format_bytes

        assert "B" in format_bytes(100)

    def test_format_bytes_kilobytes(self):
        """Test format_bytes with kilobyte range"""
        from app.main import format_bytes

        result = format_bytes(2048)
        assert "KB" in result

    def test_format_bytes_megabytes(self):
        """Test format_bytes with megabyte range"""
        from app.main import format_bytes

        result = format_bytes(2 * 1024 * 1024)
        assert "MB" in result

    def test_format_bytes_gigabytes(self):
        """Test format_bytes with gigabyte range"""
        from app.main import format_bytes

        result = format_bytes(5 * 1024 * 1024 * 1024)
        assert "GB" in result

    def test_format_duration_seconds_only(self):
        """Test format_duration with seconds only"""
        from app.main import format_duration

        delta = timedelta(seconds=45)
        assert format_duration(delta) == "45s"

    def test_format_duration_minutes_seconds(self):
        """Test format_duration with minutes and seconds"""
        from app.main import format_duration

        delta = timedelta(minutes=3, seconds=30)
        assert format_duration(delta) == "3m 30s"

    def test_format_duration_hours_minutes_seconds(self):
        """Test format_duration with hours, minutes, and seconds"""
        from app.main import format_duration

        delta = timedelta(hours=2, minutes=15, seconds=10)
        assert format_duration(delta) == "2h 15m 10s"
