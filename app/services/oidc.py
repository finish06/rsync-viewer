"""OIDC authentication service — discovery, state management, token exchange."""

import logging
import secrets
import time
import urllib.parse
from typing import Any, Optional

import httpx
import jwt as pyjwt
from cryptography.fernet import Fernet
from sqlmodel import Session, select

from app.config import get_settings
from app.models.oidc_config import OidcConfig

logger = logging.getLogger(__name__)


# --- Encryption helpers (shared Fernet key with SMTP) ---


def _get_fernet() -> Optional[Fernet]:
    """Get Fernet cipher from shared encryption key."""
    settings = get_settings()
    key = settings.effective_encryption_key
    if not key:
        return None
    return Fernet(key.encode())


def encrypt_client_secret(secret: str) -> str:
    """Encrypt a client secret using Fernet symmetric encryption."""
    fernet = _get_fernet()
    if not fernet:
        raise ValueError("ENCRYPTION_KEY is not configured")
    return fernet.encrypt(secret.encode()).decode()


def decrypt_client_secret(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted client secret."""
    fernet = _get_fernet()
    if not fernet:
        raise ValueError("ENCRYPTION_KEY is not configured")
    return fernet.decrypt(encrypted.encode()).decode()


# --- Config CRUD (singleton pattern) ---


def get_oidc_config(session: Session) -> Optional[OidcConfig]:
    """Get the singleton OIDC configuration."""
    return session.exec(select(OidcConfig).limit(1)).first()


# --- OIDC Discovery ---

# Cache discovery results in memory (issuer_url → (doc, timestamp))
_discovery_cache: dict[str, tuple[dict[str, Any], float]] = {}
_DISCOVERY_CACHE_TTL = 3600  # 1 hour


async def fetch_discovery(issuer_url: str) -> dict[str, Any]:
    """Fetch OIDC discovery document from issuer's .well-known endpoint.

    Results are cached in memory for 1 hour.
    """
    now = time.monotonic()

    # Check cache
    cached = _discovery_cache.get(issuer_url)
    if cached and (now - cached[1]) < _DISCOVERY_CACHE_TTL:
        return cached[0]

    url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        doc = response.json()

    _discovery_cache[issuer_url] = (doc, now)
    result: dict[str, Any] = doc
    return result


def clear_discovery_cache() -> None:
    """Clear the discovery cache (useful for testing)."""
    _discovery_cache.clear()


# --- State / Nonce management (in-memory, 10-minute TTL) ---

# state_value → {"nonce": str, "return_url": str, "created": float}
_pending_states: dict[str, dict[str, Any]] = {}
_STATE_TTL = 600  # 10 minutes


def _cleanup_expired_states() -> None:
    """Remove expired state entries."""
    now = time.monotonic()
    expired = [k for k, v in _pending_states.items() if now - v["created"] > _STATE_TTL]
    for k in expired:
        del _pending_states[k]


def generate_state(return_url: str = "/") -> tuple[str, str]:
    """Generate a state and nonce pair for OIDC CSRF/replay protection.

    Returns (state, nonce).
    """
    _cleanup_expired_states()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    _pending_states[state] = {
        "nonce": nonce,
        "return_url": return_url,
        "created": time.monotonic(),
    }
    return state, nonce


def validate_state(state: str) -> Optional[dict[str, Any]]:
    """Validate and consume a state parameter.

    Returns the stored data (nonce, return_url) if valid, None if invalid/expired.
    The state is consumed (deleted) on successful validation.
    """
    _cleanup_expired_states()
    data = _pending_states.pop(state, None)
    return data


def clear_pending_states() -> None:
    """Clear all pending states (useful for testing)."""
    _pending_states.clear()


# --- Auth URL building ---


async def build_authorize_url(
    config: OidcConfig,
    redirect_uri: str,
    return_url: str = "/",
) -> str:
    """Build the OIDC authorization URL for the redirect."""
    discovery = await fetch_discovery(config.issuer_url)
    authorize_endpoint: str = discovery["authorization_endpoint"]

    state, nonce = generate_state(return_url)

    params = {
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": config.scopes or "openid email profile",
        "state": state,
        "nonce": nonce,
    }

    return authorize_endpoint + "?" + urllib.parse.urlencode(params)


# --- Token exchange ---


async def exchange_code_for_tokens(
    config: OidcConfig,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange an authorization code for tokens at the provider's token endpoint."""
    discovery = await fetch_discovery(config.issuer_url)
    token_endpoint = discovery["token_endpoint"]

    client_secret = decrypt_client_secret(config.encrypted_client_secret)

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": config.client_id,
                "client_secret": client_secret,
            },
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result


def decode_id_token(
    id_token: str,
    expected_nonce: str,
    config: OidcConfig,
) -> dict[str, Any]:
    """Decode and validate an OIDC ID token.

    Validates: nonce, issuer, audience. Does NOT verify signature
    (we trust the token endpoint response over TLS).
    """
    # Decode without verification first to get claims
    # We trust the token since it came directly from the token endpoint over HTTPS
    claims = pyjwt.decode(
        id_token,
        options={
            "verify_signature": False,
            "verify_exp": True,
            "verify_iat": True,
        },
    )

    # Validate nonce
    if claims.get("nonce") != expected_nonce:
        raise ValueError("ID token nonce does not match expected value")

    # Validate issuer
    expected_issuer = config.issuer_url.rstrip("/")
    token_issuer = claims.get("iss", "").rstrip("/")
    if token_issuer != expected_issuer:
        raise ValueError(
            f"ID token issuer mismatch: expected {expected_issuer}, got {token_issuer}"
        )

    # Validate audience
    aud = claims.get("aud")
    if isinstance(aud, list):
        if config.client_id not in aud:
            raise ValueError("ID token audience does not include this client")
    elif aud != config.client_id:
        raise ValueError(
            f"ID token audience mismatch: expected {config.client_id}, got {aud}"
        )

    return claims


# --- User integration ---


def get_or_create_oidc_user(
    session: Session,
    claims: dict[str, Any],
    config: OidcConfig,
) -> Any:  # Returns User; avoid forward-ref mypy error
    """Find or create a local user from OIDC claims.

    Priority:
    1. Match by oidc_subject (returning OIDC user)
    2. Match by email (link existing local user to OIDC)
    3. Create new user with Viewer role
    """
    from app.models.user import User
    from app.services.auth import ROLE_VIEWER
    from app.utils import utc_now

    sub = claims.get("sub")
    email = claims.get("email")
    name = claims.get("preferred_username") or claims.get("name") or email

    if not sub:
        raise ValueError("OIDC claims missing required 'sub' field")
    if not email:
        raise ValueError("OIDC claims missing required 'email' field")

    issuer = config.issuer_url

    # 1. Look up by oidc_subject
    user = session.exec(select(User).where(User.oidc_subject == sub)).first()
    if user:
        # Update claims on each login (AC-017)
        # Only update email if it wouldn't conflict with another user
        if email and email != user.email:
            existing_email = session.exec(
                select(User).where(User.email == email, User.id != user.id)
            ).first()
            if not existing_email:
                user.email = email
        if name and name != user.username:
            # Only update username if it wouldn't conflict
            existing = session.exec(
                select(User).where(User.username == name, User.id != user.id)
            ).first()
            if not existing:
                user.username = name
        user.last_login_at = utc_now()
        user.updated_at = utc_now()
        session.add(user)
        session.flush()
        return user

    # 2. Look up by email (auto-link)
    user = session.exec(select(User).where(User.email == email)).first()
    if user:
        user.oidc_subject = sub
        user.oidc_issuer = issuer
        user.auth_provider = "oidc"
        user.last_login_at = utc_now()
        user.updated_at = utc_now()
        session.add(user)
        session.flush()
        return user

    # 3. Create new user
    # Ensure username is unique
    username = name
    if session.exec(select(User).where(User.username == username)).first():
        username = f"{name}_{sub[:8]}"

    user = User(
        username=username,
        email=email,
        password_hash="",  # OIDC users have no local password
        role=ROLE_VIEWER,
        auth_provider="oidc",
        oidc_subject=sub,
        oidc_issuer=issuer,
        last_login_at=utc_now(),
    )
    session.add(user)
    session.flush()
    return user
