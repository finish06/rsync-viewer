"""Integration tests for webhook dispatch triggered by sync log submission.

Covers: AC-001 (end-to-end), AC-009 (notified flag via API)
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_ac001_sync_log_failure_triggers_webhook(
    client: AsyncClient, sample_sync_log_data
):
    """Submitting a sync log with non-zero exit code triggers webhook dispatch."""
    # Create a webhook endpoint
    webhook_resp = await client.post(
        "/api/v1/webhooks",
        json={"name": "Test Hook", "url": "https://example.com/hook"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert webhook_resp.status_code == 201

    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        # Submit sync log with failure
        data = {**sample_sync_log_data, "exit_code": 1}
        response = await client.post(
            "/api/v1/sync-logs",
            json=data,
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 201

        # Webhook should have been called
        mock_client.post.assert_called_once()


@pytest.mark.anyio
async def test_ac001_successful_sync_does_not_trigger_webhook(
    client: AsyncClient, sample_sync_log_data
):
    """Submitting a sync log with exit_code=0 does not trigger webhook dispatch."""
    # Create a webhook endpoint
    await client.post(
        "/api/v1/webhooks",
        json={"name": "Test Hook", "url": "https://example.com/hook"},
        headers={"X-API-Key": "test-api-key"},
    )

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock()
        mock_client_class.return_value = mock_client

        data = {**sample_sync_log_data, "exit_code": 0}
        response = await client.post(
            "/api/v1/sync-logs",
            json=data,
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 201

        # Webhook should NOT have been called
        mock_client.post.assert_not_called()


@pytest.mark.anyio
async def test_ac009_failure_event_marked_notified_via_api(
    client: AsyncClient, sample_sync_log_data
):
    """After webhook delivery, the FailureEvent notified flag is true when queried via API."""
    # Create a webhook endpoint
    await client.post(
        "/api/v1/webhooks",
        json={"name": "Test Hook", "url": "https://example.com/hook"},
        headers={"X-API-Key": "test-api-key"},
    )

    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        data = {**sample_sync_log_data, "exit_code": 1}
        await client.post(
            "/api/v1/sync-logs",
            json=data,
            headers={"X-API-Key": "test-api-key"},
        )

    # Check failure event via API
    failures_resp = await client.get(
        "/api/v1/failures",
        headers={"X-API-Key": "test-api-key"},
    )
    failures = failures_resp.json()
    assert len(failures) == 1
    assert failures[0]["notified"] is True
