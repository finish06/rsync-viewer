"""Shared rate limiter instance for use across endpoint modules."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

settings = get_settings()


def _get_rate_limit_key(request: Request) -> str:
    """Rate limit key: API key if present, else client IP."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[settings.rate_limit_authenticated],
    headers_enabled=True,
)

# Auth-specific rate limit string — relaxed in debug/test mode
AUTH_RATE_LIMIT = "10000/minute" if settings.debug else "10/minute"
PASSWORD_RESET_RATE_LIMIT = "10000/minute" if settings.debug else "5/minute"
