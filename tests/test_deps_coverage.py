"""Tests for app/api/deps.py — covers uncovered dependency functions.

Targets:
  - _try_verify_api_key() (lines 231-284)
  - verify_api_key_or_jwt() (lines 291-375)
  - _get_api_key_effective_role() (lines 378-390)
  - require_role_or_api_key() (lines 393-424)
"""

import os
from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import jwt as pyjwt
import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.api.deps import (
    _get_api_key_effective_role,
    _try_verify_api_key,
    verify_api_key_or_jwt,
    require_role_or_api_key,
)
from app.config import Settings, get_settings
from app.models.sync_log import ApiKey
from app.models.user import User
from app.services.auth import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    hash_password,
)
from app.utils import utc_now

_TEST_SECRET = "test-secret-key"
_TEST_ALGORITHM = "HS256"


def _make_settings(**overrides) -> Settings:
    defaults = {
        "app_name": "Test",
        "debug": True,
        "database_url": "sqlite:///:memory:",
        "secret_key": _TEST_SECRET,
        "default_api_key": "test-api-key",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _make_jwt(user_id, role="operator", token_type="access", expired=False):
    now = utc_now()
    exp = now + timedelta(minutes=-5 if expired else 30)
    payload = {
        "sub": str(user_id),
        "username": "testuser",
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": exp,
    }
    return pyjwt.encode(payload, _TEST_SECRET, algorithm=_TEST_ALGORITHM)


# ── _get_api_key_effective_role ──


class TestGetApiKeyEffectiveRole:
    def test_role_override_takes_priority(self):
        api_key = MagicMock(spec=ApiKey)
        api_key.role_override = ROLE_VIEWER
        user = MagicMock(spec=User)
        user.role = ROLE_ADMIN

        assert _get_api_key_effective_role(user, api_key) == ROLE_VIEWER

    def test_user_role_when_no_override(self):
        api_key = MagicMock(spec=ApiKey)
        api_key.role_override = None
        user = MagicMock(spec=User)
        user.role = ROLE_ADMIN

        assert _get_api_key_effective_role(user, api_key) == ROLE_ADMIN

    def test_legacy_key_defaults_to_operator(self):
        api_key = MagicMock(spec=ApiKey)
        api_key.role_override = None

        assert _get_api_key_effective_role(None, api_key) == ROLE_OPERATOR

    def test_no_api_key_uses_user_role(self):
        user = MagicMock(spec=User)
        user.role = ROLE_VIEWER

        assert _get_api_key_effective_role(user, None) == ROLE_VIEWER

    def test_no_user_no_key_defaults_operator(self):
        assert _get_api_key_effective_role(None, None) == ROLE_OPERATOR


# ── _try_verify_api_key ──


class TestTryVerifyApiKey:
    @pytest.mark.asyncio
    async def test_empty_key_returns_none(self):
        session = MagicMock(spec=Session)
        settings = _make_settings()

        result = await _try_verify_api_key("", session, settings)
        assert result is None

    @pytest.mark.asyncio
    async def test_dev_key_returns_none(self):
        session = MagicMock(spec=Session)
        settings = _make_settings(debug=True, default_api_key="dev-key-123")

        result = await _try_verify_api_key("dev-key-123", session, settings)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_key_raises_401(self):
        session = MagicMock(spec=Session)
        # No keys in DB — exec().all() returns empty list
        session.exec.return_value.all.return_value = []
        settings = _make_settings(debug=False)

        with pytest.raises(HTTPException) as exc_info:
            await _try_verify_api_key("bad-key-12345678", session, settings)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.deps.verify_api_key_hash", return_value=True)
    async def test_valid_key_returns_api_key(self, mock_verify):
        api_key = MagicMock(spec=ApiKey)
        api_key.expires_at = None
        api_key.last_used_at = None

        session = MagicMock(spec=Session)
        session.exec.return_value.all.return_value = [api_key]
        settings = _make_settings(debug=False)

        result = await _try_verify_api_key("valid-key-12345678", session, settings)
        assert result is api_key

    @pytest.mark.asyncio
    @patch("app.api.deps.verify_api_key_hash", return_value=True)
    async def test_expired_key_skipped(self, mock_verify):
        expired_key = MagicMock(spec=ApiKey)
        expired_key.expires_at = utc_now() - timedelta(hours=1)

        session = MagicMock(spec=Session)
        session.exec.return_value.all.return_value = [expired_key]
        settings = _make_settings(debug=False)

        with pytest.raises(HTTPException) as exc_info:
            await _try_verify_api_key("expired-key-12345678", session, settings)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.deps.verify_api_key_hash", return_value=True)
    async def test_debounces_last_used_at(self, mock_verify):
        """last_used_at updated when stale by >5 minutes."""
        api_key = MagicMock(spec=ApiKey)
        api_key.expires_at = None
        api_key.last_used_at = utc_now() - timedelta(minutes=10)

        session = MagicMock(spec=Session)
        session.exec.return_value.all.return_value = [api_key]
        settings = _make_settings(debug=False)

        result = await _try_verify_api_key("valid-key-12345678", session, settings)
        assert result is api_key
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.deps.verify_api_key_hash", return_value=True)
    async def test_no_debounce_when_recently_used(self, mock_verify):
        """last_used_at NOT updated when used within 5 minutes."""
        api_key = MagicMock(spec=ApiKey)
        api_key.expires_at = None
        api_key.last_used_at = utc_now() - timedelta(minutes=1)

        session = MagicMock(spec=Session)
        session.exec.return_value.all.return_value = [api_key]
        settings = _make_settings(debug=False)

        result = await _try_verify_api_key("valid-key-12345678", session, settings)
        assert result is api_key
        session.add.assert_not_called()
        session.commit.assert_not_called()


# ── verify_api_key_or_jwt ──


class TestVerifyApiKeyOrJwt:
    @pytest.mark.asyncio
    async def test_no_credentials_raises_401(self):
        request = MagicMock()
        session = MagicMock(spec=Session)
        settings = _make_settings()

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key_or_jwt(
                request=request,
                session=session,
                settings=settings,
                x_api_key=None,
                authorization=None,
                access_token=None,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_auth_dev_key(self):
        request = MagicMock()
        session = MagicMock(spec=Session)
        settings = _make_settings(debug=True, default_api_key="dev-key")

        user, api_key = await verify_api_key_or_jwt(
            request=request,
            session=session,
            settings=settings,
            x_api_key="dev-key",
            authorization=None,
            access_token=None,
        )
        assert user is None
        assert api_key is None  # dev key returns None for api_key

    @pytest.mark.asyncio
    async def test_jwt_bearer_auth(self, db_session):
        user_id = uuid4()
        user = User(
            id=user_id,
            username="jwtuser",
            email="jwt@test.com",
            password_hash=hash_password("Pass1!"),
            role=ROLE_OPERATOR,
        )
        db_session.add(user)
        db_session.flush()

        os.environ["SECRET_KEY"] = _TEST_SECRET
        get_settings.cache_clear()

        token = _make_jwt(user_id, role=ROLE_OPERATOR)
        request = MagicMock()
        settings = _make_settings()

        result_user, result_key = await verify_api_key_or_jwt(
            request=request,
            session=db_session,
            settings=settings,
            x_api_key=None,
            authorization=f"Bearer {token}",
            access_token=None,
        )
        assert result_user is not None
        assert result_user.id == user_id
        assert result_key is None
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_jwt_cookie_auth(self, db_session):
        user_id = uuid4()
        user = User(
            id=user_id,
            username="cookieuser",
            email="cookie@test.com",
            password_hash=hash_password("Pass1!"),
            role=ROLE_VIEWER,
        )
        db_session.add(user)
        db_session.flush()

        os.environ["SECRET_KEY"] = _TEST_SECRET
        get_settings.cache_clear()

        token = _make_jwt(user_id, role=ROLE_VIEWER)
        request = MagicMock()
        settings = _make_settings()

        result_user, result_key = await verify_api_key_or_jwt(
            request=request,
            session=db_session,
            settings=settings,
            x_api_key=None,
            authorization=None,
            access_token=token,
        )
        assert result_user is not None
        assert result_user.id == user_id
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_expired_jwt_raises_401(self):
        user_id = uuid4()
        token = _make_jwt(user_id, expired=True)
        request = MagicMock()
        session = MagicMock(spec=Session)
        settings = _make_settings()

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key_or_jwt(
                request=request,
                session=session,
                settings=settings,
                x_api_key=None,
                authorization=f"Bearer {token}",
                access_token=None,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_type_raises_401(self):
        user_id = uuid4()
        token = _make_jwt(user_id, token_type="refresh")
        request = MagicMock()
        session = MagicMock(spec=Session)
        settings = _make_settings()

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key_or_jwt(
                request=request,
                session=session,
                settings=settings,
                x_api_key=None,
                authorization=f"Bearer {token}",
                access_token=None,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self, db_session):
        nonexistent_id = uuid4()
        os.environ["SECRET_KEY"] = _TEST_SECRET
        get_settings.cache_clear()

        token = _make_jwt(nonexistent_id)
        request = MagicMock()
        settings = _make_settings()

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key_or_jwt(
                request=request,
                session=db_session,
                settings=settings,
                x_api_key=None,
                authorization=f"Bearer {token}",
                access_token=None,
            )
        assert exc_info.value.status_code == 401
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_disabled_user_raises_403(self, db_session):
        user_id = uuid4()
        user = User(
            id=user_id,
            username="disabled",
            email="disabled@test.com",
            password_hash=hash_password("Pass1!"),
            role=ROLE_OPERATOR,
            is_active=False,
        )
        db_session.add(user)
        db_session.flush()

        os.environ["SECRET_KEY"] = _TEST_SECRET
        get_settings.cache_clear()

        token = _make_jwt(user_id)
        request = MagicMock()
        settings = _make_settings()

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key_or_jwt(
                request=request,
                session=db_session,
                settings=settings,
                x_api_key=None,
                authorization=f"Bearer {token}",
                access_token=None,
            )
        assert exc_info.value.status_code == 403
        get_settings.cache_clear()

    @pytest.mark.asyncio
    @patch("app.api.deps._try_verify_api_key")
    async def test_api_key_with_user_loads_user(self, mock_try, db_session):
        """API key with user_id loads the associated user."""
        user_id = uuid4()
        user = User(
            id=user_id,
            username="keyowner",
            email="keyowner@test.com",
            password_hash=hash_password("Pass1!"),
            role=ROLE_ADMIN,
        )
        db_session.add(user)
        db_session.flush()

        api_key = MagicMock(spec=ApiKey)
        api_key.user_id = user_id
        mock_try.return_value = api_key

        request = MagicMock()
        settings = _make_settings()

        result_user, result_key = await verify_api_key_or_jwt(
            request=request,
            session=db_session,
            settings=settings,
            x_api_key="some-api-key",
            authorization=None,
            access_token=None,
        )
        assert result_user.id == user_id
        assert result_key is api_key

    @pytest.mark.asyncio
    @patch("app.api.deps._try_verify_api_key")
    async def test_api_key_with_disabled_user_raises_403(self, mock_try, db_session):
        user_id = uuid4()
        user = User(
            id=user_id,
            username="disabled_keyowner",
            email="dk@test.com",
            password_hash=hash_password("Pass1!"),
            role=ROLE_ADMIN,
            is_active=False,
        )
        db_session.add(user)
        db_session.flush()

        api_key = MagicMock(spec=ApiKey)
        api_key.user_id = user_id
        mock_try.return_value = api_key

        request = MagicMock()
        settings = _make_settings()

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key_or_jwt(
                request=request,
                session=db_session,
                settings=settings,
                x_api_key="some-api-key",
                authorization=None,
                access_token=None,
            )
        assert exc_info.value.status_code == 403


# ── require_role_or_api_key ──


class TestRequireRoleOrApiKey:
    @pytest.mark.asyncio
    async def test_jwt_user_with_sufficient_role(self):
        user = MagicMock(spec=User)
        user.role = ROLE_ADMIN
        dep = require_role_or_api_key(ROLE_OPERATOR)
        result = await dep(auth=(user, None))
        assert result == (user, None)

    @pytest.mark.asyncio
    async def test_jwt_user_with_insufficient_role(self):
        user = MagicMock(spec=User)
        user.role = ROLE_VIEWER
        dep = require_role_or_api_key(ROLE_ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            await dep(auth=(user, None))
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_api_key_with_sufficient_role(self):
        api_key = MagicMock(spec=ApiKey)
        api_key.role_override = ROLE_ADMIN
        dep = require_role_or_api_key(ROLE_OPERATOR)
        result = await dep(auth=(None, api_key))
        assert result == (None, api_key)

    @pytest.mark.asyncio
    async def test_api_key_with_insufficient_role(self):
        api_key = MagicMock(spec=ApiKey)
        api_key.role_override = ROLE_VIEWER
        dep = require_role_or_api_key(ROLE_ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            await dep(auth=(None, api_key))
        assert exc_info.value.status_code == 403
        assert "insufficient" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_legacy_api_key_defaults_operator(self):
        """Legacy key (no user, no role_override) defaults to operator."""
        api_key = MagicMock(spec=ApiKey)
        api_key.role_override = None
        dep = require_role_or_api_key(ROLE_OPERATOR)
        result = await dep(auth=(None, api_key))
        assert result == (None, api_key)

    @pytest.mark.asyncio
    async def test_api_key_with_user_uses_effective_role(self):
        """API key + user: uses role_override if set."""
        user = MagicMock(spec=User)
        user.role = ROLE_ADMIN
        api_key = MagicMock(spec=ApiKey)
        api_key.role_override = ROLE_VIEWER

        dep = require_role_or_api_key(ROLE_ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            await dep(auth=(user, api_key))
        assert exc_info.value.status_code == 403
