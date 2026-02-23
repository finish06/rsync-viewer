"""Tests for API key last_used_at debounce.

Spec: specs/api-key-debounce.md
"""

import pytest
from datetime import timedelta
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlmodel import Session

from app.api.deps import hash_api_key
from app.config import get_settings
from app.database import get_session
from app.main import app
from app.models.sync_log import ApiKey
from app.utils import utc_now

pytestmark = pytest.mark.asyncio

# Raw test key — must hash to look up in DB
TEST_RAW_KEY = "debounce-test-key-12345"


@pytest.fixture
def create_api_key(db_session: Session):
    """Factory fixture to create an ApiKey with known raw key."""

    def _create(
        name="Test Key",
        raw_key=TEST_RAW_KEY,
        is_active=True,
        last_used_at=None,
    ):
        api_key = ApiKey(
            id=uuid4(),
            key_hash=hash_api_key(raw_key),
            name=name,
            is_active=is_active,
            last_used_at=last_used_at,
        )
        db_session.add(api_key)
        db_session.commit()
        db_session.refresh(api_key)
        return api_key

    return _create


@pytest.fixture
def real_auth_client(test_engine, db_session):
    """Client that uses real API key verification (no mock).

    This allows testing the actual debounce logic in verify_api_key.
    """
    from app.config import Settings

    def get_test_session():
        yield db_session

    def get_test_settings() -> Settings:
        return Settings(
            app_name="Rsync Log Viewer Test",
            debug=False,  # Disable debug to force DB key lookup
            database_url="postgresql+psycopg://postgres:postgres@localhost:5433/rsync_viewer_test",
            secret_key="test-secret-key",
            default_api_key="unused",
        )

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_settings] = get_test_settings

    yield AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )

    app.dependency_overrides.clear()


@pytest.fixture
def sample_sync_data():
    """Minimal valid sync log data for making authenticated requests."""
    now = utc_now()
    return {
        "source_name": "debounce-test",
        "start_time": (now - timedelta(minutes=1)).isoformat(),
        "end_time": now.isoformat(),
        "raw_content": "sent 100 bytes  received 200 bytes  300 bytes/sec\ntotal size is 1000  speedup is 10.00",
    }


class TestDebounceFirstUse:
    """AC-001: When last_used_at is NULL, timestamp is written immediately."""

    async def test_ac001_null_last_used_at_gets_set(
        self, real_auth_client, create_api_key, db_session, sample_sync_data
    ):
        """First use of an API key sets last_used_at from NULL."""
        api_key = create_api_key(last_used_at=None)
        assert api_key.last_used_at is None

        response = await real_auth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_data,
            headers={"X-API-Key": TEST_RAW_KEY},
        )
        assert response.status_code == 201

        db_session.refresh(api_key)
        assert api_key.last_used_at is not None

    async def test_ac001_first_use_timestamp_is_recent(
        self, real_auth_client, create_api_key, db_session, sample_sync_data
    ):
        """First use sets last_used_at to approximately now."""
        before = utc_now()
        api_key = create_api_key(last_used_at=None)

        await real_auth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_data,
            headers={"X-API-Key": TEST_RAW_KEY},
        )
        after = utc_now()

        db_session.refresh(api_key)
        assert before <= api_key.last_used_at <= after


class TestDebounceStaleKey:
    """AC-002: When last_used_at is older than 5 minutes, timestamp is updated."""

    async def test_ac002_stale_key_gets_updated(
        self, real_auth_client, create_api_key, db_session, sample_sync_data
    ):
        """Key used 10 minutes ago gets its last_used_at updated."""
        old_time = utc_now() - timedelta(minutes=10)
        api_key = create_api_key(last_used_at=old_time)

        before = utc_now()
        response = await real_auth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_data,
            headers={"X-API-Key": TEST_RAW_KEY},
        )
        assert response.status_code == 201

        db_session.refresh(api_key)
        assert api_key.last_used_at > old_time
        assert api_key.last_used_at >= before

    async def test_ac002_exactly_stale_key_gets_updated(
        self, real_auth_client, create_api_key, db_session, sample_sync_data
    ):
        """Key used exactly 6 minutes ago (>5 min) gets updated."""
        old_time = utc_now() - timedelta(minutes=6)
        api_key = create_api_key(last_used_at=old_time)

        await real_auth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_data,
            headers={"X-API-Key": TEST_RAW_KEY},
        )

        db_session.refresh(api_key)
        assert api_key.last_used_at > old_time


class TestDebounceFreshKey:
    """AC-003: When last_used_at is within 5 minutes, no DB write occurs."""

    async def test_ac003_recent_key_not_updated(
        self, real_auth_client, create_api_key, db_session, sample_sync_data
    ):
        """Key used 1 minute ago does NOT get last_used_at updated."""
        recent_time = utc_now() - timedelta(minutes=1)
        api_key = create_api_key(last_used_at=recent_time)

        response = await real_auth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_data,
            headers={"X-API-Key": TEST_RAW_KEY},
        )
        assert response.status_code == 201

        db_session.refresh(api_key)
        # last_used_at should still be the original time (no write)
        assert api_key.last_used_at == recent_time

    async def test_ac003_four_minute_old_key_not_updated(
        self, real_auth_client, create_api_key, db_session, sample_sync_data
    ):
        """Key used 4 minutes ago (within window) is NOT updated."""
        four_min_ago = utc_now() - timedelta(minutes=4)
        api_key = create_api_key(last_used_at=four_min_ago)

        await real_auth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_data,
            headers={"X-API-Key": TEST_RAW_KEY},
        )

        db_session.refresh(api_key)
        assert api_key.last_used_at == four_min_ago


class TestDebounceNoAuthRegression:
    """AC-004: Debounce does not affect validation behavior."""

    async def test_ac004_missing_key_still_rejected(
        self, real_auth_client, sample_sync_data
    ):
        """Missing API key still returns 401."""
        response = await real_auth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_data,
        )
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    async def test_ac004_invalid_key_still_rejected(
        self, real_auth_client, sample_sync_data
    ):
        """Invalid API key still returns 401."""
        response = await real_auth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_data,
            headers={"X-API-Key": "totally-wrong-key"},
        )
        assert response.status_code == 401
        assert "Invalid or inactive" in response.json()["detail"]

    async def test_ac004_inactive_key_still_rejected(
        self, real_auth_client, create_api_key, sample_sync_data
    ):
        """Inactive API key still returns 401."""
        create_api_key(is_active=False)

        response = await real_auth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_data,
            headers={"X-API-Key": TEST_RAW_KEY},
        )
        assert response.status_code == 401

    async def test_ac004_valid_key_still_authenticates(
        self, real_auth_client, create_api_key, sample_sync_data
    ):
        """Valid API key still authenticates successfully."""
        create_api_key()

        response = await real_auth_client.post(
            "/api/v1/sync-logs",
            json=sample_sync_data,
            headers={"X-API-Key": TEST_RAW_KEY},
        )
        assert response.status_code == 201
