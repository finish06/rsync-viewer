"""Shared webhook test payload construction and delivery.

Eliminates duplication between the HTMX webhook test handler and
the API webhook test endpoint (AC-009).
"""

from typing import Any
from uuid import UUID

import httpx
from sqlmodel import Session, select

from app.models.webhook import WebhookEndpoint
from app.models.webhook_options import WebhookOptions
from app.services.webhook_dispatcher import DEFAULT_DISCORD_COLOR


def get_webhook_options(session: Session, webhook_id: UUID) -> dict:
    """Load webhook options dict for a given endpoint, defaulting to ``{}``."""
    opts_row = session.exec(
        select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == webhook_id)
    ).first()
    return opts_row.options if opts_row else {}


def build_test_webhook_payload(
    webhook: WebhookEndpoint,
    options: dict[str, Any],
) -> dict[str, Any]:
    """Build the JSON payload for a webhook test notification.

    Returns the appropriate payload depending on ``webhook.webhook_type``:
    - ``"discord"`` → Discord embed format with optional avatar.
    - anything else → generic ``{"event": "test", ...}`` payload.
    """
    if webhook.webhook_type == "discord":
        color = options.get("color", DEFAULT_DISCORD_COLOR)
        username = options.get("username", "Rsync Viewer")
        payload: dict[str, Any] = {
            "username": username,
            "embeds": [
                {
                    "title": "Test Notification",
                    "description": "This is a test notification from Rsync Viewer.",
                    "color": color,
                }
            ],
        }
        if options.get("avatar_url"):
            payload["avatar_url"] = options["avatar_url"]
        return payload

    return {
        "event": "test",
        "message": "This is a test notification from Rsync Viewer.",
    }


def build_test_headers(
    webhook: WebhookEndpoint,
) -> dict[str, str]:
    """Build HTTP headers for a webhook test request."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if webhook.headers:
        headers.update(webhook.headers)
    return headers


async def send_test_webhook(
    webhook: WebhookEndpoint,
    payload: dict[str, Any],
    headers: dict[str, str],
) -> httpx.Response:
    """Send the test webhook POST and return the raw httpx response."""
    async with httpx.AsyncClient() as client:
        return await client.post(
            webhook.url,
            json=payload,
            headers=headers,
            timeout=10.0,
        )
