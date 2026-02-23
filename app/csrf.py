"""CSRF protection for state-changing form submissions."""

import hmac
import secrets


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def validate_csrf_token(expected: str, actual: str) -> bool:
    """Validate a CSRF token using constant-time comparison."""
    if not expected or not actual:
        return False
    return hmac.compare_digest(expected, actual)
