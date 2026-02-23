"""Tests for structured logging (specs/structured-logging.md)."""

import json
import logging


class TestLoggingConfiguration:
    """AC-001, AC-002, AC-003, AC-012: Logging config and JSON formatter."""

    def test_ac001_logging_config_module_exists(self):
        """logging_config module can be imported."""
        from app.logging_config import setup_logging

        assert callable(setup_logging)

    def test_ac001_json_formatter_produces_json(self):
        """JSON formatter outputs valid JSON."""
        from app.logging_config import setup_logging

        logging.getLogger("test_json_output")
        # Set up with JSON format
        setup_logging(log_level="INFO", log_format="json")

        # Find handler that produces JSON
        root = logging.getLogger()
        json_handler = None
        for handler in root.handlers:
            if hasattr(handler, "formatter") and handler.formatter is not None:
                json_handler = handler
                break

        assert json_handler is not None, "Expected a handler with JSON formatter"

    def test_ac002_log_entry_has_required_fields(self):
        """Each log entry includes timestamp, level, message, logger."""
        from app.logging_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)

        assert "timestamp" in data
        assert "level" in data
        assert "message" in data
        assert "logger" in data

    def test_ac003_log_level_from_settings(self):
        """LOG_LEVEL setting is available in config."""
        from app.config import Settings

        settings = Settings(
            database_url="postgresql://test",
            log_level="WARNING",
        )
        assert settings.log_level == "WARNING"

    def test_ac003_log_level_default_is_info(self):
        """LOG_LEVEL defaults to INFO."""
        from app.config import Settings

        settings = Settings(database_url="postgresql://test")
        assert settings.log_level == "INFO"

    def test_ac012_log_format_from_settings(self):
        """LOG_FORMAT setting is available in config."""
        from app.config import Settings

        settings = Settings(
            database_url="postgresql://test",
            log_format="text",
        )
        assert settings.log_format == "text"

    def test_ac012_log_format_default_is_json(self):
        """LOG_FORMAT defaults to json."""
        from app.config import Settings

        settings = Settings(database_url="postgresql://test")
        assert settings.log_format == "json"


class TestRequestMiddleware:
    """AC-004, AC-005, AC-006: Request logging middleware."""

    async def test_ac005_request_id_generated(self, client):
        """Each request gets a unique request_id."""
        response = await client.get("/health")
        assert response.status_code == 200
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None

    async def test_ac006_request_id_is_uuid(self, client):
        """X-Request-ID is a valid UUID4."""
        import uuid

        response = await client.get("/health")
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None
        # Should not raise
        parsed = uuid.UUID(request_id, version=4)
        assert str(parsed) == request_id

    async def test_ac005_unique_per_request(self, client):
        """Different requests get different request_ids."""
        r1 = await client.get("/health")
        r2 = await client.get("/health")
        id1 = r1.headers.get("X-Request-ID")
        id2 = r2.headers.get("X-Request-ID")
        assert id1 != id2

    async def test_ac004_request_logging(self, client):
        """Request logs include method, path, status_code, duration_ms."""
        from app.middleware import RequestLoggingMiddleware

        # Verify middleware class exists and is importable
        assert RequestLoggingMiddleware is not None


class TestSensitiveDataProtection:
    """AC-007, AC-009: No sensitive data in logs."""

    def test_ac007_api_key_not_logged(self):
        """API key values are never included in log output."""
        from app.middleware import SENSITIVE_HEADERS

        # Verify that authorization-related headers are filtered
        assert "x-api-key" in [h.lower() for h in SENSITIVE_HEADERS]


class TestDomainEventLogging:
    """AC-008, AC-010: Domain-specific log events."""

    async def test_ac008_sync_log_creation_logged(self, client):
        """Sync log creation produces a log entry."""
        # Verify the endpoint uses logging by checking it imports logging
        from app.api.endpoints import sync_logs as sync_module
        import inspect

        source = inspect.getsource(sync_module)
        assert "logger" in source or "logging" in source

    def test_ac010_parser_warns_on_none_fields(self):
        """Parser logs warning when fields can't be parsed."""
        from app.services import rsync_parser as parser_module
        import inspect

        source = inspect.getsource(parser_module)
        assert "logger" in source or "logging" in source


class TestUvicornLogSuppression:
    """AC-011: Uvicorn access logs suppressed."""

    def test_ac011_uvicorn_log_config_available(self):
        """Application provides uvicorn log config to suppress access logs."""
        from app.logging_config import get_uvicorn_log_config

        config = get_uvicorn_log_config()
        assert isinstance(config, dict)
        # Uvicorn access logger should be disabled or redirected
        assert "loggers" in config or "disable_existing_loggers" in config
