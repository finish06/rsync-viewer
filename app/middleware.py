"""Request logging middleware with correlation IDs."""

import logging
import time
from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Context variable for request_id correlation
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Headers that should never appear in logs
SENSITIVE_HEADERS = ["X-API-Key", "Authorization", "Cookie"]

# Paths that log at DEBUG level to reduce noise
QUIET_PATHS = {"/health", "/static"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request/response with timing and correlation ID."""

    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        rid = str(uuid4())
        request_id_var.set(rid)

        # Determine log level based on path
        path = request.url.path
        log_level = (
            logging.DEBUG
            if any(path.startswith(p) for p in QUIET_PATHS)
            else logging.INFO
        )

        start_time = time.monotonic()

        # Log request
        logger.log(
            log_level,
            "Request started",
            extra={
                "request_id": rid,
                "method": request.method,
                "path": path,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            logger.error(
                "Request failed with unhandled exception",
                extra={
                    "request_id": rid,
                    "method": request.method,
                    "path": path,
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )
            raise

        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = rid

        # Log response
        logger.log(
            log_level,
            "Request completed",
            extra={
                "request_id": rid,
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response
