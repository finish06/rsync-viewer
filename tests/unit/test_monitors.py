"""Tests for sync source monitor CRUD API.

Covers: AC-002, AC-007, AC-009, AC-010
"""

import pytest
from httpx import AsyncClient


# --- AC-007: CRUD API for monitors ---


@pytest.mark.anyio
async def test_ac007_create_monitor(client: AsyncClient):
    """POST /api/v1/monitors should create a sync source monitor."""
    data = {
        "source_name": "backup-server",
        "expected_interval_hours": 24,
    }
    response = await client.post(
        "/api/v1/monitors",
        json=data,
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    monitor = response.json()
    assert monitor["source_name"] == "backup-server"
    assert monitor["expected_interval_hours"] == 24
    assert monitor["grace_multiplier"] == 1.5  # default
    assert monitor["enabled"] is True  # default
    assert monitor["last_sync_at"] is None
    assert "id" in monitor


@pytest.mark.anyio
async def test_ac007_list_monitors(client: AsyncClient):
    """GET /api/v1/monitors should return all monitors."""
    # Create two monitors
    for name in ["server-a", "server-b"]:
        await client.post(
            "/api/v1/monitors",
            json={"source_name": name, "expected_interval_hours": 24},
            headers={"X-API-Key": "test-api-key"},
        )

    response = await client.get(
        "/api/v1/monitors",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    monitors = response.json()
    assert len(monitors) == 2


@pytest.mark.anyio
async def test_ac007_update_monitor(client: AsyncClient):
    """PUT /api/v1/monitors/{id} should update monitor fields."""
    # Create
    create_response = await client.post(
        "/api/v1/monitors",
        json={"source_name": "test-source", "expected_interval_hours": 24},
        headers={"X-API-Key": "test-api-key"},
    )
    monitor_id = create_response.json()["id"]

    # Update
    response = await client.put(
        f"/api/v1/monitors/{monitor_id}",
        json={"expected_interval_hours": 48, "enabled": False},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["expected_interval_hours"] == 48
    assert updated["enabled"] is False
    assert updated["source_name"] == "test-source"  # unchanged


@pytest.mark.anyio
async def test_ac007_delete_monitor(client: AsyncClient):
    """DELETE /api/v1/monitors/{id} should remove the monitor."""
    # Create
    create_response = await client.post(
        "/api/v1/monitors",
        json={"source_name": "to-delete", "expected_interval_hours": 24},
        headers={"X-API-Key": "test-api-key"},
    )
    monitor_id = create_response.json()["id"]

    # Delete
    response = await client.delete(
        f"/api/v1/monitors/{monitor_id}",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 204

    # Verify gone
    list_response = await client.get(
        "/api/v1/monitors",
        headers={"X-API-Key": "test-api-key"},
    )
    assert len(list_response.json()) == 0


@pytest.mark.anyio
async def test_ac007_create_duplicate_source_returns_409(client: AsyncClient):
    """Creating a monitor for an existing source_name should return 409."""
    data = {"source_name": "duplicate", "expected_interval_hours": 24}
    await client.post(
        "/api/v1/monitors",
        json=data,
        headers={"X-API-Key": "test-api-key"},
    )
    response = await client.post(
        "/api/v1/monitors",
        json=data,
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_ac007_update_nonexistent_returns_404(client: AsyncClient):
    """PUT for a non-existent monitor ID should return 404."""
    response = await client.put(
        "/api/v1/monitors/00000000-0000-0000-0000-000000000000",
        json={"expected_interval_hours": 48},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_ac007_delete_nonexistent_returns_404(client: AsyncClient):
    """DELETE for a non-existent monitor ID should return 404."""
    response = await client.delete(
        "/api/v1/monitors/00000000-0000-0000-0000-000000000000",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_ac007_create_requires_api_key(unauth_client: AsyncClient):
    """Monitor endpoints should require authentication."""
    response = await unauth_client.post(
        "/api/v1/monitors",
        json={"source_name": "test", "expected_interval_hours": 24},
    )
    assert response.status_code == 401


# --- AC-002: Configurable expected sync frequency ---


@pytest.mark.anyio
async def test_ac002_configurable_frequency(client: AsyncClient):
    """Monitor should accept various frequency values."""
    for hours in [24, 168, 336]:  # daily, weekly, bi-weekly
        response = await client.post(
            "/api/v1/monitors",
            json={
                "source_name": f"source-{hours}h",
                "expected_interval_hours": hours,
            },
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 201
        assert response.json()["expected_interval_hours"] == hours


# --- AC-010: Configurable grace multiplier ---


@pytest.mark.anyio
async def test_ac010_custom_grace_multiplier(client: AsyncClient):
    """Monitor should accept a custom grace multiplier."""
    response = await client.post(
        "/api/v1/monitors",
        json={
            "source_name": "custom-grace",
            "expected_interval_hours": 24,
            "grace_multiplier": 2.0,
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    assert response.json()["grace_multiplier"] == 2.0


@pytest.mark.anyio
async def test_ac010_default_grace_multiplier(client: AsyncClient):
    """Monitor without explicit grace_multiplier should default to 1.5."""
    response = await client.post(
        "/api/v1/monitors",
        json={"source_name": "default-grace", "expected_interval_hours": 24},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    assert response.json()["grace_multiplier"] == 1.5
