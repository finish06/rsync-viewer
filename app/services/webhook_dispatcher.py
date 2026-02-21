"""Webhook dispatcher service — dispatches failure notifications to configured webhook endpoints."""

import asyncio
import logging

import httpx
from sqlmodel import Session, select

from app.models.failure_event import FailureEvent
from app.models.notification_log import NotificationLog
from app.models.webhook import WebhookEndpoint

logger = logging.getLogger(__name__)

# Retry delays in seconds (exponential backoff)
RETRY_DELAYS = [30, 60, 120]
MAX_ATTEMPTS = 3
AUTO_DISABLE_THRESHOLD = 10
REQUEST_TIMEOUT = 10.0


def _build_payload(event: FailureEvent) -> dict:
    """Build the webhook JSON payload from a FailureEvent."""
    return {
        "event": "failure_detected",
        "source_name": event.source_name,
        "failure_type": event.failure_type,
        "details": event.details,
        "detected_at": event.detected_at.isoformat(),
        "sync_log_id": str(event.sync_log_id) if event.sync_log_id else None,
        "failure_event_id": str(event.id),
    }


async def _deliver_to_endpoint(
    client: httpx.AsyncClient,
    webhook: WebhookEndpoint,
    payload: dict,
) -> tuple[bool, int | None, str | None]:
    """Attempt to deliver payload to a single webhook endpoint.

    Returns (success, http_status_code, error_message).
    """
    headers = {"Content-Type": "application/json"}
    if webhook.headers:
        headers.update(webhook.headers)

    try:
        response = await client.post(
            webhook.url,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        if 200 <= response.status_code < 300:
            return True, response.status_code, None
        return False, response.status_code, f"HTTP {response.status_code}"
    except httpx.TimeoutException:
        return False, None, "Request timed out"
    except httpx.RequestError as e:
        return False, None, str(e)


async def dispatch_webhooks(session: Session, event: FailureEvent) -> None:
    """Dispatch webhook notifications for a failure event.

    Sends HTTP POST to all enabled webhook endpoints with retry
    on failure. Logs each attempt to NotificationLog. Auto-disables
    endpoints after AUTO_DISABLE_THRESHOLD consecutive failures.
    Sets event.notified=True if at least one endpoint succeeds.
    """
    webhooks = session.exec(
        select(WebhookEndpoint).where(WebhookEndpoint.enabled.is_(True))
    ).all()

    if not webhooks:
        return

    payload = _build_payload(event)
    any_success = False

    async with httpx.AsyncClient() as client:
        for webhook in webhooks:
            success = False

            for attempt in range(1, MAX_ATTEMPTS + 1):
                ok, status_code, error_msg = await _deliver_to_endpoint(
                    client, webhook, payload
                )

                # Log the attempt
                log_entry = NotificationLog(
                    failure_event_id=event.id,
                    webhook_endpoint_id=webhook.id,
                    status="success" if ok else "failed",
                    http_status_code=status_code,
                    error_message=error_msg,
                    attempt_number=attempt,
                )
                session.add(log_entry)
                session.commit()

                if ok:
                    success = True
                    break

                # Wait before retry (except on last attempt)
                if attempt < MAX_ATTEMPTS:
                    delay = RETRY_DELAYS[attempt - 1]
                    await asyncio.sleep(delay)

            if success:
                # Reset consecutive failures on success
                webhook.consecutive_failures = 0
                session.add(webhook)
                session.commit()
                any_success = True
            else:
                # Increment consecutive failures
                webhook.consecutive_failures += 1
                if webhook.consecutive_failures >= AUTO_DISABLE_THRESHOLD:
                    webhook.enabled = False
                    logger.warning(
                        "Webhook auto-disabled after %d consecutive failures",
                        webhook.consecutive_failures,
                        extra={"webhook_id": str(webhook.id), "webhook_name": webhook.name},
                    )
                session.add(webhook)
                session.commit()

    if any_success:
        event.notified = True
        session.add(event)
        session.commit()
