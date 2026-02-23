"""Request logging and security middleware."""

import logging
import time
from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.csrf import validate_csrf_token

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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        settings = get_settings()

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        csp = "default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self'"
        if settings.csp_report_only:
            response.headers["Content-Security-Policy-Report-Only"] = csp
        else:
            response.headers["Content-Security-Policy"] = csp

        if settings.hsts_enabled:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"

        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies exceeding the configured limit."""

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > settings.max_request_body_size:
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=413,
                content={
                    "error_code": "PAYLOAD_TOO_LARGE",
                    "message": f"Request body exceeds maximum size of {settings.max_request_body_size} bytes",
                },
            )

        return await call_next(request)


# Paths where CSRF validation is enforced for form POSTs
CSRF_PROTECTED_PREFIXES = ("/htmx/webhooks",)

# Methods that are state-changing and require CSRF validation
CSRF_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class CsrfMiddleware(BaseHTTPMiddleware):
    """Validate CSRF tokens on state-changing form submissions."""

    async def dispatch(self, request: Request, call_next):
        if (
            request.method in CSRF_METHODS
            and any(
                request.url.path.startswith(p) for p in CSRF_PROTECTED_PREFIXES
            )
        ):
            # Check for CSRF token in form data or header
            csrf_token = request.headers.get("X-CSRF-Token", "")
            cookie_token = request.cookies.get("csrf_token", "")

            if not csrf_token or not validate_csrf_token(cookie_token, csrf_token):
                from starlette.responses import JSONResponse

                return JSONResponse(
                    status_code=403,
                    content={
                        "error_code": "CSRF_VALIDATION_FAILED",
                        "message": "CSRF token missing or invalid",
                    },
                )

        return await call_next(request)
