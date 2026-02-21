"""Tests for failure detection — exit code failures and sync log modifications.

Covers: AC-001, AC-011
"""

import pytest
from httpx import AsyncClient


# --- AC-001: Non-zero exit code creates FailureEvent ---


@pytest.mark.anyio
async def test_ac001_nonzero_exit_code_creates_failure_event(
    client: AsyncClient, db_session, sample_sync_log_data
):
    """Submitting a sync log with non-zero exit_code should create a FailureEvent."""
    data = {**sample_sync_log_data, "exit_code": 1}
    response = await client.post(
        "/api/v1/sync-logs",
        json=data,
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    sync_log = response.json()
    assert sync_log["exit_code"] == 1

    # Verify a FailureEvent was created
    failures_response = await client.get(
        "/api/v1/failures",
        headers={"X-API-Key": "test-api-key"},
    )
    assert failures_response.status_code == 200
    failures = failures_response.json()
    assert len(failures) == 1
    assert failures[0]["failure_type"] == "exit_code"
    assert failures[0]["source_name"] == data["source_name"]
    assert failures[0]["sync_log_id"] == sync_log["id"]
    assert failures[0]["notified"] is False


@pytest.mark.anyio
async def test_ac001_exit_code_zero_no_failure_event(
    client: AsyncClient, sample_sync_log_data
):
    """Submitting a sync log with exit_code=0 should NOT create a FailureEvent."""
    data = {**sample_sync_log_data, "exit_code": 0}
    response = await client.post(
        "/api/v1/sync-logs",
        json=data,
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201

    failures_response = await client.get(
        "/api/v1/failures",
        headers={"X-API-Key": "test-api-key"},
    )
    assert failures_response.status_code == 200
    assert len(failures_response.json()) == 0


@pytest.mark.anyio
async def test_ac001_failure_event_has_details(
    client: AsyncClient, sample_sync_log_data
):
    """FailureEvent should include human-readable details about the exit code."""
    data = {**sample_sync_log_data, "exit_code": 23}
    response = await client.post(
        "/api/v1/sync-logs",
        json=data,
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201

    failures_response = await client.get(
        "/api/v1/failures",
        headers={"X-API-Key": "test-api-key"},
    )
    failures = failures_response.json()
    assert "23" in failures[0]["details"]


# --- AC-011: Existing logs without exit_code treated as success ---


@pytest.mark.anyio
async def test_ac011_no_exit_code_treated_as_success(
    client: AsyncClient, sample_sync_log_data
):
    """Sync log without exit_code field should be treated as successful."""
    # Original data has no exit_code
    response = await client.post(
        "/api/v1/sync-logs",
        json=sample_sync_log_data,
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    sync_log = response.json()
    assert sync_log["exit_code"] is None

    # No failure event created
    failures_response = await client.get(
        "/api/v1/failures",
        headers={"X-API-Key": "test-api-key"},
    )
    assert len(failures_response.json()) == 0


# --- Sync log updates monitor last_sync_at ---


@pytest.mark.anyio
async def test_sync_log_updates_monitor_last_sync_at(
    client: AsyncClient, sample_sync_log_data
):
    """Submitting a sync log should update the matching monitor's last_sync_at."""
    # Create a monitor for the same source
    await client.post(
        "/api/v1/monitors",
        json={
            "source_name": sample_sync_log_data["source_name"],
            "expected_interval_hours": 24,
        },
        headers={"X-API-Key": "test-api-key"},
    )

    response = await client.post(
        "/api/v1/sync-logs",
        json=sample_sync_log_data,
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201

    monitors_response = await client.get(
        "/api/v1/monitors",
        headers={"X-API-Key": "test-api-key"},
    )
    monitors = monitors_response.json()
    assert len(monitors) == 1
    assert monitors[0]["last_sync_at"] is not None
