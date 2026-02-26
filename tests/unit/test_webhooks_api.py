"""Tests for webhook endpoints CRUD API.

Covers: AC-002, AC-008, AC-011
"""

import pytest
from httpx import AsyncClient


# --- AC-002: CRUD API endpoints for webhook endpoints ---


@pytest.mark.anyio
async def test_ac002_create_webhook(client: AsyncClient):
    """POST /api/v1/webhooks creates a webhook endpoint."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "Test Hook",
            "url": "https://example.com/hook",
            "enabled": True,
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    webhook = response.json()
    assert webhook["name"] == "Test Hook"
    assert webhook["url"] == "https://example.com/hook"
    assert webhook["enabled"] is True
    assert webhook["consecutive_failures"] == 0
    assert "id" in webhook


@pytest.mark.anyio
async def test_ac002_list_webhooks(client: AsyncClient):
    """GET /api/v1/webhooks lists all webhook endpoints."""
    # Create two webhooks
    await client.post(
        "/api/v1/webhooks",
        json={"name": "Hook A", "url": "https://a.com/hook"},
        headers={"X-API-Key": "test-api-key"},
    )
    await client.post(
        "/api/v1/webhooks",
        json={"name": "Hook B", "url": "https://b.com/hook"},
        headers={"X-API-Key": "test-api-key"},
    )

    response = await client.get(
        "/api/v1/webhooks",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    webhooks = response.json()
    assert len(webhooks) == 2


@pytest.mark.anyio
async def test_ac002_update_webhook(client: AsyncClient):
    """PUT /api/v1/webhooks/{id} updates a webhook endpoint."""
    create_resp = await client.post(
        "/api/v1/webhooks",
        json={"name": "Original", "url": "https://example.com/hook"},
        headers={"X-API-Key": "test-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/webhooks/{webhook_id}",
        json={"name": "Updated", "enabled": False},
        headers={"X-API-Key": "test-api-key"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "Updated"
    assert updated["enabled"] is False
    # URL should remain unchanged
    assert updated["url"] == "https://example.com/hook"


@pytest.mark.anyio
async def test_ac002_delete_webhook(client: AsyncClient):
    """DELETE /api/v1/webhooks/{id} deletes a webhook endpoint."""
    create_resp = await client.post(
        "/api/v1/webhooks",
        json={"name": "To Delete", "url": "https://example.com/hook"},
        headers={"X-API-Key": "test-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-API-Key": "test-api-key"},
    )
    assert delete_resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get(
        "/api/v1/webhooks",
        headers={"X-API-Key": "test-api-key"},
    )
    assert len(list_resp.json()) == 0


@pytest.mark.anyio
async def test_ac002_update_nonexistent_returns_404(client: AsyncClient):
    """PUT /api/v1/webhooks/{id} returns 404 for nonexistent webhook."""
    response = await client.put(
        "/api/v1/webhooks/00000000-0000-0000-0000-000000000000",
        json={"name": "nope"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_ac002_delete_nonexistent_returns_404(client: AsyncClient):
    """DELETE /api/v1/webhooks/{id} returns 404 for nonexistent webhook."""
    response = await client.delete(
        "/api/v1/webhooks/00000000-0000-0000-0000-000000000000",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_ac002_requires_auth(unauth_client: AsyncClient):
    """Webhook endpoints require authentication."""
    response = await unauth_client.get("/api/v1/webhooks")
    assert response.status_code == 401


# --- AC-008: Custom headers support ---


@pytest.mark.anyio
async def test_ac008_create_webhook_with_custom_headers(client: AsyncClient):
    """Webhook endpoints support configurable custom headers."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "Auth Hook",
            "url": "https://example.com/hook",
            "headers": {"Authorization": "Bearer xyz123", "X-Custom": "value"},
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    webhook = response.json()
    assert webhook["headers"]["Authorization"] == "Bearer xyz123"
    assert webhook["headers"]["X-Custom"] == "value"


@pytest.mark.anyio
async def test_ac008_update_webhook_headers(client: AsyncClient):
    """Webhook custom headers can be updated."""
    create_resp = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "Hook",
            "url": "https://example.com/hook",
            "headers": {"Old": "header"},
        },
        headers={"X-API-Key": "test-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/webhooks/{webhook_id}",
        json={"headers": {"New": "header"}},
        headers={"X-API-Key": "test-api-key"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["headers"] == {"New": "header"}


# --- AC-011: Disabled webhooks skipped ---


@pytest.mark.anyio
async def test_ac011_create_disabled_webhook(client: AsyncClient):
    """Can create a webhook in disabled state."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "Disabled Hook",
            "url": "https://example.com/hook",
            "enabled": False,
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    assert response.json()["enabled"] is False
