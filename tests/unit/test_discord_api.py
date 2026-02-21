"""Tests for Discord webhook API endpoints.

Covers: AC-005, AC-006, AC-008, AC-009, AC-012, AC-013
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.models.webhook import WebhookEndpoint
from app.models.webhook_options import WebhookOptions


# --- AC-012: webhook_type and source_filters on WebhookEndpoint ---


@pytest.mark.anyio
async def test_ac012_create_webhook_with_type_and_filters(client, db_session):
    """Create webhook with webhook_type and source_filters."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "discord-alerts",
            "url": "https://discord.com/api/webhooks/123/abc",
            "webhook_type": "discord",
            "source_filters": ["server-a", "server-b"],
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["webhook_type"] == "discord"
    assert data["source_filters"] == ["server-a", "server-b"]


@pytest.mark.anyio
async def test_ac012_create_webhook_defaults_to_generic(client, db_session):
    """Webhook type defaults to 'generic' when not specified."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "generic-hook",
            "url": "https://example.com/hook",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["webhook_type"] == "generic"
    assert data["source_filters"] is None


# --- AC-013: WebhookOptions model ---


@pytest.mark.anyio
async def test_ac013_create_webhook_with_options(client, db_session):
    """Creating a discord webhook with options creates a WebhookOptions row."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "discord-with-opts",
            "url": "https://discord.com/api/webhooks/123/abc",
            "webhook_type": "discord",
            "options": {
                "color": 65280,
                "username": "My Bot",
                "avatar_url": "https://example.com/avatar.png",
                "footer": "My Footer",
            },
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["options"]["color"] == 65280
    assert data["options"]["username"] == "My Bot"


@pytest.mark.anyio
async def test_ac013_update_webhook_options(client, db_session):
    """Updating a webhook's options updates the WebhookOptions row."""
    # Create first
    create_resp = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "discord-update-test",
            "url": "https://discord.com/api/webhooks/123/abc",
            "webhook_type": "discord",
            "options": {"color": 16711680},
        },
        headers={"X-API-Key": "test-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    # Update options
    update_resp = await client.put(
        f"/api/v1/webhooks/{webhook_id}",
        json={
            "options": {"color": 65280, "username": "Updated Bot"},
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["options"]["color"] == 65280
    assert data["options"]["username"] == "Updated Bot"


@pytest.mark.anyio
async def test_ac013_delete_webhook_cascades_options(client, db_session):
    """Deleting a webhook also deletes associated WebhookOptions."""
    # Create webhook with options
    create_resp = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "discord-delete-test",
            "url": "https://discord.com/api/webhooks/123/abc",
            "webhook_type": "discord",
            "options": {"color": 16711680},
        },
        headers={"X-API-Key": "test-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    # Delete
    delete_resp = await client.delete(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-API-Key": "test-api-key"},
    )
    assert delete_resp.status_code == 204

    # Verify options are gone
    options = db_session.exec(
        select(WebhookOptions)
    ).all()
    # Filter in Python since session may have stale data
    remaining = [o for o in options if str(o.webhook_endpoint_id) == webhook_id]
    assert len(remaining) == 0


# --- AC-008: Discord URL validation ---


@pytest.mark.anyio
async def test_ac008_valid_discord_url_accepted(client, db_session):
    """Valid Discord webhook URLs are accepted."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "valid-discord",
            "url": "https://discord.com/api/webhooks/123456/abcdef",
            "webhook_type": "discord",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_ac008_valid_discordapp_url_accepted(client, db_session):
    """Valid discordapp.com webhook URLs are also accepted."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "valid-discordapp",
            "url": "https://discordapp.com/api/webhooks/123456/abcdef",
            "webhook_type": "discord",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_ac008_invalid_discord_url_rejected(client, db_session):
    """Non-Discord URLs are rejected when webhook_type is discord."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "invalid-discord",
            "url": "https://example.com/not-discord",
            "webhook_type": "discord",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_ac008_generic_webhook_allows_any_url(client, db_session):
    """Generic webhooks accept any URL (no Discord validation)."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "generic-any-url",
            "url": "https://example.com/any-hook",
            "webhook_type": "generic",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 201


# --- AC-009: Test message endpoint ---


@pytest.mark.anyio
async def test_ac009_test_endpoint_sends_message(client, db_session):
    """POST /webhooks/{id}/test sends a test notification."""
    # Create webhook
    create_resp = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "test-message-hook",
            "url": "https://discord.com/api/webhooks/123/abc",
            "webhook_type": "discord",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    mock_response = AsyncMock()
    mock_response.status_code = 204

    with patch("app.api.endpoints.webhooks.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        response = await client.post(
            f"/api/v1/webhooks/{webhook_id}/test",
            headers={"X-API-Key": "test-api-key"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"


@pytest.mark.anyio
async def test_ac009_test_endpoint_404_for_missing(client, db_session):
    """POST /webhooks/{id}/test returns 404 for non-existent webhook."""
    fake_id = uuid4()
    response = await client.post(
        f"/api/v1/webhooks/{fake_id}/test",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_ac009_test_endpoint_reports_delivery_failure(client, db_session):
    """POST /webhooks/{id}/test returns 502 when delivery fails."""
    create_resp = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "test-fail-hook",
            "url": "https://discord.com/api/webhooks/123/abc",
            "webhook_type": "discord",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    mock_response = AsyncMock()
    mock_response.status_code = 500

    with patch("app.api.endpoints.webhooks.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        response = await client.post(
            f"/api/v1/webhooks/{webhook_id}/test",
            headers={"X-API-Key": "test-api-key"},
        )

    assert response.status_code == 502


# --- AC-006: source_filters in API ---


@pytest.mark.anyio
async def test_ac006_update_source_filters(client, db_session):
    """Source filters can be updated on a webhook."""
    create_resp = await client.post(
        "/api/v1/webhooks",
        json={
            "name": "filter-test",
            "url": "https://example.com/hook",
            "source_filters": ["server-a"],
        },
        headers={"X-API-Key": "test-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/webhooks/{webhook_id}",
        json={"source_filters": ["server-a", "server-b"]},
        headers={"X-API-Key": "test-api-key"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["source_filters"] == ["server-a", "server-b"]


# --- AC-005: List webhooks includes options ---


@pytest.mark.anyio
async def test_ac005_list_webhooks_includes_options(client, db_session):
    """GET /webhooks returns options for each webhook."""
    await client.post(
        "/api/v1/webhooks",
        json={
            "name": "discord-list-test",
            "url": "https://discord.com/api/webhooks/123/abc",
            "webhook_type": "discord",
            "options": {"color": 16711680},
        },
        headers={"X-API-Key": "test-api-key"},
    )

    response = await client.get(
        "/api/v1/webhooks",
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 200
    webhooks = response.json()
    assert len(webhooks) >= 1
    discord_hook = next(w for w in webhooks if w["name"] == "discord-list-test")
    assert discord_hook["options"]["color"] == 16711680
