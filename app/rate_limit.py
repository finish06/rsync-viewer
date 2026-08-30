"""Shared rate limiter instance for use across endpoint modules.

The limiter is keyed on the client IP only (AC-003). Keying on the
``X-API-Key`` header would let an attacker mint a fresh bucket per guessed
key, turning the brute-force limit into no limit at all.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

settings = get_settings()

# One bucket per client IP. In debug/test mode the shared bucket would be
# exhausted by the test suite itself, so it is relaxed the same way as the
# auth-specific limits below.
_DEFAULT_LIMIT = "10000/minute" if settings.debug else settings.rate_limit_authenticated

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_DEFAULT_LIMIT],
    headers_enabled=True,
)

# Auth-specific rate limit string — relaxed in debug/test mode
AUTH_RATE_LIMIT = "10000/minute" if settings.debug else "10/minute"
PASSWORD_RESET_RATE_LIMIT = "10000/minute" if settings.debug else "5/minute"
