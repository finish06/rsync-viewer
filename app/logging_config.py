"""Structured logging configuration with JSON and text formatters."""

import logging
import sys
from datetime import datetime, timezone

from pythonjsonlogger import json as json_logger


class JsonFormatter(json_logger.JsonFormatter):
    """Custom JSON formatter that ensures required fields are present."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        if "message" not in log_record:
            log_record["message"] = record.getMessage()


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
) -> None:
    """Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format - 'json' for structured JSON, 'text' for human-readable.
    """
    # Validate and set log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
        logging.warning("Invalid LOG_LEVEL '%s', defaulting to INFO", log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root_logger.addHandler(handler)


def get_uvicorn_log_config() -> dict:
    """Return uvicorn log config that suppresses default access logs."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            "uvicorn.access": {
                "level": "WARNING",
                "handlers": [],
                "propagate": False,
            },
        },
    }
