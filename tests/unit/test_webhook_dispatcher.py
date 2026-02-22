"""Tests for webhook dispatcher service.

Covers: AC-001, AC-003, AC-004, AC-005, AC-006, AC-009, AC-010, AC-011
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.models.failure_event import FailureEvent
from app.models.notification_log import NotificationLog
from app.models.webhook import WebhookEndpoint
from app.services.webhook_dispatcher import dispatch_webhooks


@pytest.fixture
def create_webhook(db_session: Session):
    """Factory fixture to create webhook endpoints in the database."""

    def _create(
        name: str = "test-webhook",
        url: str = "https://example.com/hook",
        headers: dict = None,
        enabled: bool = True,
        consecutive_failures: int = 0,
    ) -> WebhookEndpoint:
        webhook = WebhookEndpoint(
            id=uuid4(),
            name=name,
            url=url,
            headers=headers,
            enabled=enabled,
            consecutive_failures=consecutive_failures,
        )
        db_session.add(webhook)
        db_session.commit()
        db_session.refresh(webhook)
        return webhook

    return _create


@pytest.fixture
def create_failure_event(db_session: Session):
    """Factory fixture to create failure events in the database."""

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


# --- AC-001: Enabled webhooks receive POST on FailureEvent ---


@pytest.mark.anyio
async def test_ac001_webhook_receives_post_on_failure(
    db_session, create_webhook, create_failure_event
):
    """When a FailureEvent is created, enabled webhooks receive HTTP POST."""
    create_webhook(url="https://example.com/hook")
    event = create_failure_event()

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

        await dispatch_webhooks(db_session, event)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://example.com/hook"


# --- AC-003: Payload includes required fields ---


@pytest.mark.anyio
async def test_ac003_payload_includes_required_fields(
    db_session, create_webhook, create_failure_event
):
    """Webhook payload includes source_name, failure_type, details, detected_at."""
    create_webhook()
    event = create_failure_event(
        source_name="backup-server",
        failure_type="exit_code",
        details="rsync exited with code 23",
    )

    captured_payload = {}
    mock_response = AsyncMock()
    mock_response.status_code = 200

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

    assert captured_payload["event"] == "failure_detected"
    assert captured_payload["source_name"] == "backup-server"
    assert captured_payload["failure_type"] == "exit_code"
    assert captured_payload["details"] == "rsync exited with code 23"
    assert "detected_at" in captured_payload
    assert "failure_event_id" in captured_payload


# --- AC-004: Retry with exponential backoff ---


@pytest.mark.anyio
async def test_ac004_retries_on_failure(
    db_session, create_webhook, create_failure_event
):
    """Failed deliveries are retried up to 3 times."""
    create_webhook()
    event = create_failure_event()

    mock_response = AsyncMock()
    mock_response.status_code = 500

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch(
            "app.services.webhook_dispatcher.asyncio.sleep", new_callable=AsyncMock
        ):
            await dispatch_webhooks(db_session, event)

        # Should have been called 3 times (initial + 2 retries)
        assert mock_client.post.call_count == 3


# --- AC-005: Delivery attempts logged in NotificationLog ---


@pytest.mark.anyio
async def test_ac005_delivery_logged(db_session, create_webhook, create_failure_event):
    """Each delivery attempt is logged in NotificationLog."""
    webhook = create_webhook()
    event = create_failure_event()

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

        await dispatch_webhooks(db_session, event)

    logs = db_session.exec(
        select(NotificationLog).where(NotificationLog.failure_event_id == event.id)
    ).all()
    assert len(logs) == 1
    assert logs[0].status == "success"
    assert logs[0].http_status_code == 200
    assert logs[0].attempt_number == 1
    assert logs[0].webhook_endpoint_id == webhook.id


@pytest.mark.anyio
async def test_ac005_failed_attempts_all_logged(
    db_session, create_webhook, create_failure_event
):
    """All retry attempts are logged when delivery fails."""
    create_webhook()
    event = create_failure_event()

    mock_response = AsyncMock()
    mock_response.status_code = 500

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch(
            "app.services.webhook_dispatcher.asyncio.sleep", new_callable=AsyncMock
        ):
            await dispatch_webhooks(db_session, event)

    logs = db_session.exec(
        select(NotificationLog)
        .where(NotificationLog.failure_event_id == event.id)
        .order_by(NotificationLog.attempt_number)
    ).all()
    assert len(logs) == 3
    assert logs[0].attempt_number == 1
    assert logs[1].attempt_number == 2
    assert logs[2].attempt_number == 3
    assert all(log.status == "failed" for log in logs)


# --- AC-006: Auto-disable after 10 consecutive failures ---


@pytest.mark.anyio
async def test_ac006_auto_disable_after_10_consecutive_failures(
    db_session, create_webhook, create_failure_event
):
    """Webhook is auto-disabled after 10 consecutive failures."""
    webhook = create_webhook(consecutive_failures=9)
    event = create_failure_event()

    mock_response = AsyncMock()
    mock_response.status_code = 500

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch(
            "app.services.webhook_dispatcher.asyncio.sleep", new_callable=AsyncMock
        ):
            await dispatch_webhooks(db_session, event)

    db_session.refresh(webhook)
    assert webhook.enabled is False
    assert webhook.consecutive_failures >= 10


@pytest.mark.anyio
async def test_ac006_success_resets_consecutive_failures(
    db_session, create_webhook, create_failure_event
):
    """Successful delivery resets consecutive_failures to 0."""
    webhook = create_webhook(consecutive_failures=5)
    event = create_failure_event()

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

        await dispatch_webhooks(db_session, event)

    db_session.refresh(webhook)
    assert webhook.consecutive_failures == 0


# --- AC-009: FailureEvent.notified set to True on success ---


@pytest.mark.anyio
async def test_ac009_failure_event_notified_on_success(
    db_session, create_webhook, create_failure_event
):
    """After successful delivery, FailureEvent.notified is set to True."""
    create_webhook()
    event = create_failure_event()
    assert event.notified is False

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

        await dispatch_webhooks(db_session, event)

    db_session.refresh(event)
    assert event.notified is True


@pytest.mark.anyio
async def test_ac009_failure_event_not_notified_on_all_failures(
    db_session, create_webhook, create_failure_event
):
    """If all deliveries fail, FailureEvent.notified stays False."""
    create_webhook()
    event = create_failure_event()

    mock_response = AsyncMock()
    mock_response.status_code = 500

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with patch(
            "app.services.webhook_dispatcher.asyncio.sleep", new_callable=AsyncMock
        ):
            await dispatch_webhooks(db_session, event)

    db_session.refresh(event)
    assert event.notified is False


# --- AC-010: Synchronous dispatch ---


@pytest.mark.anyio
async def test_ac010_dispatch_is_called_inline(
    db_session, create_webhook, create_failure_event
):
    """Webhook dispatch happens synchronously (inline), not via scheduler."""
    create_webhook()
    event = create_failure_event()

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

        # dispatch_webhooks should complete synchronously (awaitable)
        await dispatch_webhooks(db_session, event)

    # Verify it completed — notification log exists
    logs = db_session.exec(
        select(NotificationLog).where(NotificationLog.failure_event_id == event.id)
    ).all()
    assert len(logs) == 1


# --- AC-011: Disabled webhooks skipped ---


@pytest.mark.anyio
async def test_ac011_disabled_webhooks_skipped(
    db_session, create_webhook, create_failure_event
):
    """Disabled webhooks are not called during dispatch."""
    create_webhook(name="disabled", enabled=False)
    event = create_failure_event()

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
async def test_ac011_mixed_enabled_disabled(
    db_session, create_webhook, create_failure_event
):
    """Only enabled webhooks are called; disabled ones are skipped."""
    create_webhook(name="enabled", url="https://enabled.com/hook", enabled=True)
    create_webhook(name="disabled", url="https://disabled.com/hook", enabled=False)
    event = create_failure_event()

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

        await dispatch_webhooks(db_session, event)

        # Only one call (enabled webhook)
        assert mock_client.post.call_count == 1
        call_url = mock_client.post.call_args[0][0]
        assert call_url == "https://enabled.com/hook"


# --- AC-008: Custom headers sent with webhook ---


@pytest.mark.anyio
async def test_ac008_custom_headers_sent(
    db_session, create_webhook, create_failure_event
):
    """Custom headers are included in the webhook POST request."""
    create_webhook(headers={"Authorization": "Bearer token123", "X-Custom": "value"})
    event = create_failure_event()

    captured_headers = {}
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch(
        "app.services.webhook_dispatcher.httpx.AsyncClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def capture_post(url, json=None, headers=None, timeout=None):
            captured_headers.update(headers or {})
            return mock_response

        mock_client.post = capture_post
        mock_client_class.return_value = mock_client

        await dispatch_webhooks(db_session, event)

    assert captured_headers.get("Authorization") == "Bearer token123"
    assert captured_headers.get("X-Custom") == "value"


# --- No webhooks configured ---


@pytest.mark.anyio
async def test_no_webhooks_configured(db_session, create_failure_event):
    """No error when no webhook endpoints exist."""
    event = create_failure_event()

    # Should complete without error
    await dispatch_webhooks(db_session, event)

    db_session.refresh(event)
    assert event.notified is False
