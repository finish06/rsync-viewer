"""Tests for OIDC authentication flow (specs/oidc-authentication.md).

Covers: A-AC-001 through A-AC-017 (excluding superseded AC-009).
"""

import os
import time
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.main import app
from app.models.oidc_config import OidcConfig
from app.models.user import User
from app.services.auth import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    hash_password,
)
from app.services.oidc import (
    clear_discovery_cache,
    clear_pending_states,
    decode_id_token,
    encrypt_client_secret,
    generate_state,
    validate_state,
)
from app.utils import utc_now

_TEST_SECRET = "test-secret-key"
_TEST_ALGORITHM = "HS256"
_TEST_FERNET_KEY = Fernet.generate_key().decode()


def _make_jwt(user_id: str, username: str, role: str) -> str:
    now = utc_now()
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    return pyjwt.encode(payload, _TEST_SECRET, algorithm=_TEST_ALGORITHM)


def _setup_overrides(db_session: Session):
    from tests.conftest import get_test_settings

    os.environ["SECRET_KEY"] = _TEST_SECRET
    os.environ["DEBUG"] = "true"
    os.environ["DEFAULT_API_KEY"] = "test-api-key"
    os.environ["SMTP_ENCRYPTION_KEY"] = _TEST_FERNET_KEY
    get_settings.cache_clear()

    def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings


def _cleanup():
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    os.environ.pop("SMTP_ENCRYPTION_KEY", None)
    clear_pending_states()
    clear_discovery_cache()


def _create_user(
    db_session: Session,
    username: str = "testuser",
    role: str = ROLE_ADMIN,
    email: str = None,
    auth_provider: str = "local",
) -> User:
    user = User(
        username=username,
        email=email or f"{username}@test.local",
        password_hash=hash_password("TestPass1!"),
        role=role,
        auth_provider=auth_provider,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_oidc_config(
    db_session: Session,
    admin: User,
    enabled: bool = True,
    hide_local_login: bool = False,
) -> OidcConfig:
    config = OidcConfig(
        issuer_url="https://auth.example.com",
        client_id="rsync-viewer",
        encrypted_client_secret=encrypt_client_secret("test-secret"),
        provider_name="PocketId",
        enabled=enabled,
        hide_local_login=hide_local_login,
        scopes="openid email profile",
        configured_by_id=admin.id,
    )
    db_session.add(config)
    db_session.flush()
    return config


def _make_client(user: User = None) -> AsyncClient:
    cookies = {}
    if user:
        jwt_token = _make_jwt(str(user.id), user.username, user.role)
        cookies["access_token"] = jwt_token
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies=cookies,
    )


# --- State / Nonce management tests ---


class TestStateNonceManagement:
    """A-AC-013: State validation. A-AC-014: Nonce validation."""

    def test_ac013_generate_state_returns_unique_values(self):
        s1, n1 = generate_state("/")
        s2, n2 = generate_state("/")
        assert s1 != s2
        assert n1 != n2

    def test_ac013_validate_state_returns_data(self):
        state, nonce = generate_state("/dashboard")
        data = validate_state(state)
        assert data is not None
        assert data["nonce"] == nonce
        assert data["return_url"] == "/dashboard"

    def test_ac013_validate_state_consumed_on_use(self):
        state, _ = generate_state("/")
        assert validate_state(state) is not None
        assert validate_state(state) is None  # Second use fails

    def test_ac013_validate_state_rejects_invalid(self):
        assert validate_state("bogus-state") is None

    def test_ac013_validate_state_rejects_expired(self):
        state, _ = generate_state("/")
        # Manually expire it
        from app.services.oidc import _pending_states

        _pending_states[state]["created"] = time.monotonic() - 700
        assert validate_state(state) is None


# --- ID Token validation tests ---


class TestIdTokenValidation:
    """A-AC-004: ID token validation. A-AC-014: Nonce validation."""

    def _make_config(self) -> OidcConfig:
        return OidcConfig(
            issuer_url="https://auth.example.com",
            client_id="rsync-viewer",
            encrypted_client_secret="",
            provider_name="Test",
        )

    def _make_id_token(self, claims: dict) -> str:
        return pyjwt.encode(claims, "unused", algorithm="HS256")

    def test_ac014_nonce_mismatch_raises(self):
        config = self._make_config()
        token = self._make_id_token(
            {
                "sub": "user1",
                "nonce": "wrong-nonce",
                "iss": "https://auth.example.com",
                "aud": "rsync-viewer",
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
            }
        )
        with pytest.raises(ValueError, match="nonce"):
            decode_id_token(token, "expected-nonce", config)

    def test_ac004_issuer_mismatch_raises(self):
        config = self._make_config()
        token = self._make_id_token(
            {
                "sub": "user1",
                "nonce": "test-nonce",
                "iss": "https://evil.example.com",
                "aud": "rsync-viewer",
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
            }
        )
        with pytest.raises(ValueError, match="issuer"):
            decode_id_token(token, "test-nonce", config)

    def test_ac004_audience_mismatch_raises(self):
        config = self._make_config()
        token = self._make_id_token(
            {
                "sub": "user1",
                "nonce": "test-nonce",
                "iss": "https://auth.example.com",
                "aud": "wrong-client",
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
            }
        )
        with pytest.raises(ValueError, match="audience"):
            decode_id_token(token, "test-nonce", config)

    def test_ac004_valid_token_returns_claims(self):
        config = self._make_config()
        token = self._make_id_token(
            {
                "sub": "user1",
                "email": "user@example.com",
                "nonce": "test-nonce",
                "iss": "https://auth.example.com",
                "aud": "rsync-viewer",
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
            }
        )
        claims = decode_id_token(token, "test-nonce", config)
        assert claims["sub"] == "user1"
        assert claims["email"] == "user@example.com"


# --- OIDC Login endpoint ---


class TestOidcLogin:
    """A-AC-003: Auth Code Flow redirect. A-AC-010: Discovery. A-AC-011: Scopes."""

    @pytest.mark.anyio
    async def test_ac003_login_redirects_to_provider(self, test_engine, db_session):
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-admin", ROLE_ADMIN)
        _create_oidc_config(db_session, admin)

        mock_discovery = {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
        }

        with patch(
            "app.services.oidc.fetch_discovery",
            new_callable=AsyncMock,
            return_value=mock_discovery,
        ):
            async with _make_client() as client:
                response = await client.get("/auth/oidc/login", follow_redirects=False)
        _cleanup()

        assert response.status_code == 302
        location = response.headers["location"]
        assert "auth.example.com/authorize" in location
        assert "client_id=rsync-viewer" in location
        assert "response_type=code" in location

    @pytest.mark.anyio
    async def test_ac011_login_requests_correct_scopes(self, test_engine, db_session):
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-scopes", ROLE_ADMIN)
        _create_oidc_config(db_session, admin)

        mock_discovery = {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
        }

        with patch(
            "app.services.oidc.fetch_discovery",
            new_callable=AsyncMock,
            return_value=mock_discovery,
        ):
            async with _make_client() as client:
                response = await client.get("/auth/oidc/login", follow_redirects=False)
        _cleanup()

        location = response.headers["location"]
        assert "scope=openid" in location or "scope=openid+email+profile" in location

    @pytest.mark.anyio
    async def test_ac015_login_redirects_when_not_configured(
        self, test_engine, db_session
    ):
        """A-AC-015: No OIDC config → redirect back to login."""
        _setup_overrides(db_session)

        async with _make_client() as client:
            response = await client.get("/auth/oidc/login", follow_redirects=False)
        _cleanup()

        assert response.status_code == 302
        assert "/login" in response.headers["location"]


# --- OIDC Callback endpoint ---


class TestOidcCallback:
    """A-AC-004: Token exchange. A-AC-005: Auto-create. A-AC-006: Auto-link. A-AC-008: JWT session."""

    def _make_id_token_str(self, sub="user1", email="user@example.com", nonce="n"):
        return pyjwt.encode(
            {
                "sub": sub,
                "email": email,
                "preferred_username": "oidcuser",
                "nonce": nonce,
                "iss": "https://auth.example.com",
                "aud": "rsync-viewer",
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
            },
            "unused",
            algorithm="HS256",
        )

    @pytest.mark.anyio
    async def test_ac004_callback_exchanges_code(self, test_engine, db_session):
        """Callback exchanges code and sets session cookie."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-cb-admin", ROLE_ADMIN)
        _create_oidc_config(db_session, admin)

        state, nonce = generate_state("/")
        id_token = self._make_id_token_str(nonce=nonce)

        with patch(
            "app.routes.auth.exchange_code_for_tokens",
            new_callable=AsyncMock,
            return_value={"id_token": id_token, "access_token": "at"},
        ):
            async with _make_client() as client:
                response = await client.get(
                    f"/auth/oidc/callback?code=test-code&state={state}",
                    follow_redirects=False,
                )
        _cleanup()

        assert response.status_code == 302
        # Should have set access_token cookie
        assert any("access_token" in c for c in response.headers.get_list("set-cookie"))

    @pytest.mark.anyio
    async def test_ac005_callback_creates_new_user(self, test_engine, db_session):
        """A-AC-005: New user auto-created with Viewer role."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-create-admin", ROLE_ADMIN)
        _create_oidc_config(db_session, admin)

        state, nonce = generate_state("/")
        id_token = self._make_id_token_str(
            sub="new-oidc-user", email="newuser@example.com", nonce=nonce
        )

        with patch(
            "app.routes.auth.exchange_code_for_tokens",
            new_callable=AsyncMock,
            return_value={"id_token": id_token, "access_token": "at"},
        ):
            async with _make_client() as client:
                await client.get(
                    f"/auth/oidc/callback?code=test-code&state={state}",
                    follow_redirects=False,
                )

        new_user = db_session.exec(
            select(User).where(User.oidc_subject == "new-oidc-user")
        ).first()
        _cleanup()

        assert new_user is not None
        assert new_user.role == ROLE_VIEWER
        assert new_user.auth_provider == "oidc"
        assert new_user.email == "newuser@example.com"

    @pytest.mark.anyio
    async def test_ac006_callback_links_existing_user(self, test_engine, db_session):
        """A-AC-006: Existing user with matching email gets linked."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-link-admin", ROLE_ADMIN)
        _create_oidc_config(db_session, admin)

        existing = _create_user(
            db_session,
            "existing-user",
            ROLE_OPERATOR,
            email="existing@example.com",
        )
        original_role = existing.role

        state, nonce = generate_state("/")
        id_token = self._make_id_token_str(
            sub="oidc-sub-link", email="existing@example.com", nonce=nonce
        )

        with patch(
            "app.routes.auth.exchange_code_for_tokens",
            new_callable=AsyncMock,
            return_value={"id_token": id_token, "access_token": "at"},
        ):
            async with _make_client() as client:
                await client.get(
                    f"/auth/oidc/callback?code=test-code&state={state}",
                    follow_redirects=False,
                )

        db_session.refresh(existing)
        _cleanup()

        assert existing.oidc_subject == "oidc-sub-link"
        assert existing.auth_provider == "oidc"
        assert existing.role == original_role  # Role preserved

    @pytest.mark.anyio
    async def test_ac013_callback_rejects_invalid_state(self, test_engine, db_session):
        """A-AC-013: Invalid state parameter → redirect to login."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-bad-state", ROLE_ADMIN)
        _create_oidc_config(db_session, admin)

        async with _make_client() as client:
            response = await client.get(
                "/auth/oidc/callback?code=test-code&state=bogus",
                follow_redirects=False,
            )
        _cleanup()

        assert response.status_code == 302
        assert "error" in response.headers["location"]

    @pytest.mark.anyio
    async def test_ac016_logout_is_local_only(self, test_engine, db_session):
        """A-AC-016: Logout destroys local session only."""
        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-logout", ROLE_ADMIN)

        async with _make_client(admin) as client:
            response = await client.post("/logout", follow_redirects=False)
        _cleanup()

        assert response.status_code == 302
        assert "/login" in response.headers["location"]
        # Should NOT redirect to any OIDC provider
        assert "auth.example.com" not in response.headers["location"]


# --- Password guard ---


class TestOidcPasswordGuard:
    """A-AC-007: OIDC-created users cannot set a local password."""

    @pytest.mark.anyio
    async def test_ac007_oidc_user_cannot_request_password_reset(
        self, test_engine, db_session
    ):
        """OIDC user attempting password reset gets rejected."""
        _setup_overrides(db_session)
        oidc_user = _create_user(
            db_session,
            "oidc-only-user",
            ROLE_VIEWER,
            auth_provider="oidc",
        )

        async with _make_client(oidc_user) as client:
            response = await client.post(
                "/api/v1/auth/password-reset/request",
                json={"email": oidc_user.email},
                headers={"X-API-Key": "test-api-key"},
            )
        _cleanup()

        # Should return 200 with SSO message (no info leakage)
        assert response.status_code == 200
        data = response.json()
        assert "SSO" in data["message"] or "identity provider" in data["message"]


# --- Edge cases ---


class TestOidcEdgeCases:
    """Edge cases from spec section 7."""

    def test_no_email_claim_raises(self, test_engine, db_session):
        """OIDC claims missing email → error."""
        from app.services.oidc import get_or_create_oidc_user

        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-edge-admin", ROLE_ADMIN)
        config = _create_oidc_config(db_session, admin)

        claims = {"sub": "user-no-email", "preferred_username": "nomail"}

        with pytest.raises(ValueError, match="email"):
            get_or_create_oidc_user(db_session, claims, config)
        _cleanup()

    def test_no_sub_claim_raises(self, test_engine, db_session):
        """OIDC claims missing sub → error."""
        from app.services.oidc import get_or_create_oidc_user

        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-nosub-admin", ROLE_ADMIN)
        config = _create_oidc_config(db_session, admin)

        claims = {"email": "user@example.com"}

        with pytest.raises(ValueError, match="sub"):
            get_or_create_oidc_user(db_session, claims, config)
        _cleanup()

    def test_sub_takes_precedence_over_email(self, test_engine, db_session):
        """When sub maps to user A and email matches user B, sub wins."""
        from app.services.oidc import get_or_create_oidc_user

        _setup_overrides(db_session)
        admin = _create_user(db_session, "oidc-prec-admin", ROLE_ADMIN)
        config = _create_oidc_config(db_session, admin)

        user_a = _create_user(db_session, "user-a", ROLE_OPERATOR, email="a@test.local")
        user_a.oidc_subject = "sub-123"
        user_a.auth_provider = "oidc"
        db_session.flush()

        _create_user(db_session, "user-b", ROLE_VIEWER, email="b@test.local")

        claims = {
            "sub": "sub-123",
            "email": "b@test.local",
            "preferred_username": "oidcuser",
        }
        result = get_or_create_oidc_user(db_session, claims, config)
        _cleanup()

        assert result.id == user_a.id  # sub match wins
