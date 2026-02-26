"""Tests for failures API endpoint.

Covers: AC-008
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.models.failure_event import FailureEvent
from app.utils import utc_now


@pytest.fixture
def create_failure_event(db_session: Session):
    """Factory fixture to create failure events in the database."""

    def _create(
        source_name: str = "test-source",
        failure_type: str = "exit_code",
        sync_log_id=None,
        notified: bool = False,
        details: str = "Test failure",
        detected_at: datetime = None,
    ) -> FailureEvent:
        event = FailureEvent(
            id=uuid4(),
            source_name=source_name,
            failure_type=failure_type,
            detected_at=detected_at or utc_now(),
            sync_log_id=sync_log_id,
            notified=notified,
            details=details,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        return event

    return _create


# --- AC-008: GET /api/v1/failures ---


@pytest.mark.anyio
async def test_ac008_list_failures(client: AsyncClient, create_failure_event):
    """GET /api/v1/failures should return all failure events."""
    create_failure_event(source_name="server-a", failure_type="exit_code")
    create_failure_event(source_name="server-b", failure_type="stale")

    response = await client.get(
        "/api/v1/failures",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    failures = response.json()
    assert len(failures) == 2


@pytest.mark.anyio
async def test_ac008_filter_by_source_name(client: AsyncClient, create_failure_event):
    """GET /api/v1/failures?source_name=X should filter by source."""
    create_failure_event(source_name="server-a")
    create_failure_event(source_name="server-b")

    response = await client.get(
        "/api/v1/failures?source_name=server-a",
        headers={"X-API-Key": "test-api-key"},
    )
    failures = response.json()
    assert len(failures) == 1
    assert failures[0]["source_name"] == "server-a"


@pytest.mark.anyio
async def test_ac008_filter_by_failure_type(client: AsyncClient, create_failure_event):
    """GET /api/v1/failures?failure_type=stale should filter by type."""
    create_failure_event(failure_type="exit_code")
    create_failure_event(failure_type="stale")

    response = await client.get(
        "/api/v1/failures?failure_type=stale",
        headers={"X-API-Key": "test-api-key"},
    )
    failures = response.json()
    assert len(failures) == 1
    assert failures[0]["failure_type"] == "stale"


@pytest.mark.anyio
async def test_ac008_filter_by_notified(client: AsyncClient, create_failure_event):
    """GET /api/v1/failures?notified=false should filter unnotified events."""
    create_failure_event(notified=False)
    create_failure_event(notified=True)

    response = await client.get(
        "/api/v1/failures?notified=false",
        headers={"X-API-Key": "test-api-key"},
    )
    failures = response.json()
    assert len(failures) == 1
    assert failures[0]["notified"] is False


@pytest.mark.anyio
async def test_ac008_filter_by_since(client: AsyncClient, create_failure_event):
    """GET /api/v1/failures?since=X should filter by detected_at."""
    old = utc_now() - timedelta(days=7)
    recent = utc_now() - timedelta(hours=1)
    create_failure_event(detected_at=old, details="old event")
    create_failure_event(detected_at=recent, details="recent event")

    since = (utc_now() - timedelta(days=1)).isoformat()
    response = await client.get(
        f"/api/v1/failures?since={since}",
        headers={"X-API-Key": "test-api-key"},
    )
    failures = response.json()
    assert len(failures) == 1
    assert failures[0]["details"] == "recent event"


@pytest.mark.anyio
async def test_ac008_requires_api_key(unauth_client: AsyncClient):
    """Failures endpoint should require authentication."""
    response = await unauth_client.get("/api/v1/failures")
    assert response.status_code == 401
