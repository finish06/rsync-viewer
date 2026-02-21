"""Tests for Discord webhook dispatcher functionality.

Covers: AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-010, AC-011
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlmodel import Session

from app.models.failure_event import FailureEvent
from app.models.webhook import WebhookEndpoint
from app.models.webhook_options import WebhookOptions
from app.services.webhook_dispatcher import dispatch_webhooks


@pytest.fixture
def create_webhook(db_session: Session):
    """Factory fixture to create webhook endpoints."""

    def _create(
        name: str = "test-webhook",
        url: str = "https://example.com/hook",
        headers: dict = None,
        webhook_type: str = "generic",
        source_filters: list = None,
        enabled: bool = True,
        consecutive_failures: int = 0,
    ) -> WebhookEndpoint:
        webhook = WebhookEndpoint(
            id=uuid4(),
            name=name,
            url=url,
            headers=headers,
            webhook_type=webhook_type,
            source_filters=source_filters,
            enabled=enabled,
            consecutive_failures=consecutive_failures,
        )
        db_session.add(webhook)
        db_session.commit()
        db_session.refresh(webhook)
        return webhook

    return _create


@pytest.fixture
def create_webhook_options(db_session: Session):
    """Factory fixture to create webhook options."""

    def _create(
        webhook_endpoint_id,
        options: dict = None,
    ) -> WebhookOptions:
        opts = WebhookOptions(
            id=uuid4(),
            webhook_endpoint_id=webhook_endpoint_id,
            options=options or {},
        )
        db_session.add(opts)
        db_session.commit()
        db_session.refresh(opts)
        return opts

    return _create


@pytest.fixture
def create_failure_event(db_session: Session):
    """Factory fixture to create failure events."""

    def _create(
        source_name: str = "test-source",
        failure_type: str = "exit_code",
        details: str = "rsync exited with code 1",
        sync_log_id=None,
    ) -> FailureEvent:
        event = FailureEvent(
            id=uuid4(),
            source_name=source_name,
            failure_type=failure_type,
            details=details,
            sync_log_id=sync_log_id,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        return event

    return _create


# --- AC-001: Discord embed format ---


@pytest.mark.anyio
async def test_ac001_discord_webhook_sends_embed_format(
    db_session, create_webhook, create_webhook_options, create_failure_event
):
    """Discord webhooks send payload with embeds array (Discord execute format)."""
    webhook = create_webhook(
        url="https://discord.com/api/webhooks/123/abc",
        webhook_type="discord",
    )
    create_webhook_options(webhook.id, {"color": 16711680})
    event = create_failure_event()

    captured_payload = {}
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.headers = {}

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def capture_post(url, json=None, headers=None, timeout=None):
            captured_payload.update(json)
            return mock_response

        mock_client.post = capture_post
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

    assert "embeds" in captured_payload
    assert isinstance(captured_payload["embeds"], list)
    assert len(captured_payload["embeds"]) == 1


# --- AC-002: Embed includes structured fields ---


@pytest.mark.anyio
async def test_ac002_discord_embed_includes_required_fields(
    db_session, create_webhook, create_webhook_options, create_failure_event
):
    """Discord embed includes source_name, failure_type, details, detected_at fields."""
    webhook = create_webhook(
        url="https://discord.com/api/webhooks/123/abc",
        webhook_type="discord",
    )
    create_webhook_options(webhook.id)
    event = create_failure_event(
        source_name="backup-server",
        failure_type="exit_code",
        details="rsync exited with code 23",
    )

    captured_payload = {}
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.headers = {}

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def capture_post(url, json=None, headers=None, timeout=None):
            captured_payload.update(json)
            return mock_response

        mock_client.post = capture_post
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

    embed = captured_payload["embeds"][0]
    field_names = [f["name"] for f in embed["fields"]]
    assert "Source" in field_names
    assert "Failure Type" in field_names
    assert "Details" in field_names
    assert "Detected At" in field_names

    # Check field values
    fields_by_name = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields_by_name["Source"] == "backup-server"
    assert fields_by_name["Failure Type"] == "exit_code"
    assert "rsync exited with code 23" in fields_by_name["Details"]


# --- AC-003: Configurable color ---


@pytest.mark.anyio
async def test_ac003_discord_embed_uses_configured_color(
    db_session, create_webhook, create_webhook_options, create_failure_event
):
    """Discord embed uses color from webhook options."""
    webhook = create_webhook(
        url="https://discord.com/api/webhooks/123/abc",
        webhook_type="discord",
    )
    create_webhook_options(webhook.id, {"color": 65280})  # green
    event = create_failure_event()

    captured_payload = {}
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.headers = {}

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def capture_post(url, json=None, headers=None, timeout=None):
            captured_payload.update(json)
            return mock_response

        mock_client.post = capture_post
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

    embed = captured_payload["embeds"][0]
    assert embed["color"] == 65280


@pytest.mark.anyio
async def test_ac003_discord_embed_defaults_to_red(
    db_session, create_webhook, create_webhook_options, create_failure_event
):
    """Discord embed defaults to red (16711680) when no color specified."""
    webhook = create_webhook(
        url="https://discord.com/api/webhooks/123/abc",
        webhook_type="discord",
    )
    create_webhook_options(webhook.id, {})  # no color
    event = create_failure_event()

    captured_payload = {}
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.headers = {}

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def capture_post(url, json=None, headers=None, timeout=None):
            captured_payload.update(json)
            return mock_response

        mock_client.post = capture_post
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

    embed = captured_payload["embeds"][0]
    assert embed["color"] == 16711680


# --- AC-004: Dashboard link in embed ---


@pytest.mark.anyio
async def test_ac004_discord_embed_includes_dashboard_link(
    db_session, create_webhook, create_webhook_options, create_failure_event
):
    """Discord embed includes a URL field linking to the dashboard."""
    webhook = create_webhook(
        url="https://discord.com/api/webhooks/123/abc",
        webhook_type="discord",
    )
    create_webhook_options(webhook.id)
    event = create_failure_event()

    captured_payload = {}
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.headers = {}

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def capture_post(url, json=None, headers=None, timeout=None):
            captured_payload.update(json)
            return mock_response

        mock_client.post = capture_post
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

    embed = captured_payload["embeds"][0]
    # Embed should have a URL or a field with a link
    assert "url" in embed or any(
        "http" in f.get("value", "") for f in embed.get("fields", [])
    )


# --- AC-005: Discord options from WebhookOptions ---


@pytest.mark.anyio
async def test_ac005_discord_uses_username_and_avatar(
    db_session, create_webhook, create_webhook_options, create_failure_event
):
    """Discord payload includes username and avatar_url from options."""
    webhook = create_webhook(
        url="https://discord.com/api/webhooks/123/abc",
        webhook_type="discord",
    )
    create_webhook_options(webhook.id, {
        "username": "Rsync Bot",
        "avatar_url": "https://example.com/bot.png",
        "footer": "Rsync Viewer Alerts",
    })
    event = create_failure_event()

    captured_payload = {}
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.headers = {}

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def capture_post(url, json=None, headers=None, timeout=None):
            captured_payload.update(json)
            return mock_response

        mock_client.post = capture_post
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

    assert captured_payload.get("username") == "Rsync Bot"
    assert captured_payload.get("avatar_url") == "https://example.com/bot.png"
    embed = captured_payload["embeds"][0]
    assert embed.get("footer", {}).get("text") == "Rsync Viewer Alerts"


# --- AC-006, AC-007: Source filters ---


@pytest.mark.anyio
async def test_ac006_source_filter_allows_matching_source(
    db_session, create_webhook, create_failure_event
):
    """Webhook with source_filters delivers when source matches."""
    create_webhook(
        url="https://example.com/hook",
        source_filters=["backup-server", "nas-sync"],
    )
    event = create_failure_event(source_name="backup-server")

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

        mock_client.post.assert_called_once()


@pytest.mark.anyio
async def test_ac007_source_filter_skips_non_matching_source(
    db_session, create_webhook, create_failure_event
):
    """Webhook with source_filters skips when source not in list."""
    create_webhook(
        url="https://example.com/hook",
        source_filters=["server-a"],
    )
    event = create_failure_event(source_name="server-b")

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock()
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

        mock_client.post.assert_not_called()


@pytest.mark.anyio
async def test_ac006_null_source_filter_sends_to_all(
    db_session, create_webhook, create_failure_event
):
    """Webhook with null source_filters delivers for any source."""
    create_webhook(
        url="https://example.com/hook",
        source_filters=None,
    )
    event = create_failure_event(source_name="any-source")

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

        mock_client.post.assert_called_once()


# --- AC-010: Discord rate limit handling ---


@pytest.mark.anyio
async def test_ac010_discord_429_respects_retry_after(
    db_session, create_webhook, create_webhook_options, create_failure_event
):
    """On 429, dispatcher waits for Retry-After duration then retries."""
    webhook = create_webhook(
        url="https://discord.com/api/webhooks/123/abc",
        webhook_type="discord",
    )
    create_webhook_options(webhook.id)
    event = create_failure_event()

    rate_limit_response = AsyncMock()
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"Retry-After": "2"}

    success_response = AsyncMock()
    success_response.status_code = 204
    success_response.headers = {}

    call_count = 0

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def mock_post(url, json=None, headers=None, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return rate_limit_response
            return success_response

        mock_client.post = mock_post
        mock_client_class.return_value = mock_client

        with patch(
            "app.services.webhook_dispatcher.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await dispatch_webhooks(db_session, event)

            # Should have slept for 2 seconds (from Retry-After)
            mock_sleep.assert_any_call(2.0)

    assert call_count == 2  # First 429, then success


# --- AC-011: Generic webhooks unchanged ---


@pytest.mark.anyio
async def test_ac011_generic_webhook_sends_original_payload(
    db_session, create_webhook, create_failure_event
):
    """Generic webhooks still send the original flat JSON payload."""
    create_webhook(
        url="https://example.com/hook",
        webhook_type="generic",
    )
    event = create_failure_event()

    captured_payload = {}
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {}

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def capture_post(url, json=None, headers=None, timeout=None):
            captured_payload.update(json)
            return mock_response

        mock_client.post = capture_post
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

    # Generic payload should NOT have embeds
    assert "embeds" not in captured_payload
    # Should have the original flat fields
    assert captured_payload["event"] == "failure_detected"
    assert "source_name" in captured_payload
    assert "failure_type" in captured_payload


# --- AC-005: Discord without options uses defaults ---


@pytest.mark.anyio
async def test_ac005_discord_without_options_uses_defaults(
    db_session, create_webhook, create_failure_event
):
    """Discord webhook with no WebhookOptions row uses default color and username."""
    create_webhook(
        url="https://discord.com/api/webhooks/123/abc",
        webhook_type="discord",
    )
    # Note: no create_webhook_options call
    event = create_failure_event()

    captured_payload = {}
    mock_response = AsyncMock()
    mock_response.status_code = 204
    mock_response.headers = {}

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def capture_post(url, json=None, headers=None, timeout=None):
            captured_payload.update(json)
            return mock_response

        mock_client.post = capture_post
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

    assert "embeds" in captured_payload
    embed = captured_payload["embeds"][0]
    assert embed["color"] == 16711680  # default red
    assert captured_payload.get("username") == "Rsync Viewer"
