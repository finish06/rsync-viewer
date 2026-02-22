"""Webhook dispatcher service — dispatches failure notifications to configured webhook endpoints."""

import asyncio
import logging

import httpx
from sqlmodel import Session, select

from app.models.failure_event import FailureEvent
from app.models.notification_log import NotificationLog
from app.models.webhook import WebhookEndpoint
from app.models.webhook_options import WebhookOptions

logger = logging.getLogger(__name__)

# Retry delays in seconds (exponential backoff)
RETRY_DELAYS = [30, 60, 120]
MAX_ATTEMPTS = 3
AUTO_DISABLE_THRESHOLD = 10
REQUEST_TIMEOUT = 10.0
DEFAULT_DISCORD_COLOR = 16711680  # Red
DEFAULT_DISCORD_USERNAME = "Rsync Viewer"


def _build_payload(event: FailureEvent) -> dict:
    """Build the generic webhook JSON payload from a FailureEvent."""
    return {
        "event": "failure_detected",
        "source_name": event.source_name,
        "failure_type": event.failure_type,
        "details": event.details,
        "detected_at": event.detected_at.isoformat(),
        "sync_log_id": str(event.sync_log_id) if event.sync_log_id else None,
        "failure_event_id": str(event.id),
    }


def _build_discord_payload(event: FailureEvent, options: dict | None) -> dict:
    """Build a Discord execute-webhook payload with embeds."""
    opts = options or {}
    color = opts.get("color", DEFAULT_DISCORD_COLOR)
    username = opts.get("username", DEFAULT_DISCORD_USERNAME)
    avatar_url = opts.get("avatar_url")
    footer_text = opts.get("footer")

    embed = {
        "title": "Rsync Failure Detected",
        "color": color,
        "url": f"/htmx/sync-detail/{event.sync_log_id}"
        if event.sync_log_id
        else "http://localhost:8000/",
        "fields": [
            {"name": "Source", "value": event.source_name, "inline": True},
            {"name": "Failure Type", "value": event.failure_type, "inline": True},
            {"name": "Details", "value": event.details or "No details available"},
            {
                "name": "Detected At",
                "value": event.detected_at.isoformat(),
                "inline": True,
            },
        ],
    }

    if footer_text:
        embed["footer"] = {"text": footer_text}

    payload = {
        "username": username,
        "embeds": [embed],
    }

    if avatar_url:
        payload["avatar_url"] = avatar_url

    return payload


def _should_deliver(webhook: WebhookEndpoint, event: FailureEvent) -> bool:
    """Check if the webhook should receive this event based on source filters."""
    if webhook.source_filters is None:
        return True
    return event.source_name in webhook.source_filters


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
        # Handle Discord rate limiting
        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", "5"))
            await asyncio.sleep(retry_after)
            # Retry after waiting
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

    any_success = False

    # Batch load webhook options for all Discord webhooks to avoid N+1 queries
    discord_webhook_ids = [
        wh.id
        for wh in webhooks
        if wh.webhook_type == "discord" and _should_deliver(wh, event)
    ]
    options_map: dict = {}
    if discord_webhook_ids:
        all_opts = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id.in_(discord_webhook_ids)
            )
        ).all()
        options_map = {opt.webhook_endpoint_id: opt.options for opt in all_opts}

    async with httpx.AsyncClient() as client:
        for webhook in webhooks:
            # Source filter check
            if not _should_deliver(webhook, event):
                continue

            # Build payload based on webhook type
            if webhook.webhook_type == "discord":
                options_dict = options_map.get(webhook.id)
                payload = _build_discord_payload(event, options_dict)
            else:
                payload = _build_payload(event)

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

                if ok:
                    success = True
                    break

                # Wait before retry (except on last attempt)
                if attempt < MAX_ATTEMPTS:
                    delay = RETRY_DELAYS[attempt - 1]
                    await asyncio.sleep(delay)

            if success:
                webhook.consecutive_failures = 0
                any_success = True
            else:
                webhook.consecutive_failures += 1
                if webhook.consecutive_failures >= AUTO_DISABLE_THRESHOLD:
                    webhook.enabled = False
                    logger.warning(
                        "Webhook auto-disabled after %d consecutive failures",
                        webhook.consecutive_failures,
                        extra={
                            "webhook_id": str(webhook.id),
                            "webhook_name": webhook.name,
                        },
                    )
            session.add(webhook)

    if any_success:
        event.notified = True
        session.add(event)

    # Single commit for all log entries and status updates
    session.commit()
