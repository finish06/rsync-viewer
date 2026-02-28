import logging
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from app.api.deps import SessionDep, require_role_or_api_key
from app.services.auth import ROLE_OPERATOR, ROLE_VIEWER
from app.services.webhook_test import (
    build_test_headers,
    build_test_webhook_payload,
    get_webhook_options,
    send_test_webhook,
)
from app.utils import utc_now
from app.models.webhook import WebhookEndpoint
from app.models.webhook_options import WebhookOptions
from app.schemas.webhook import WebhookCreate, WebhookUpdate, WebhookRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _webhook_to_read(webhook: WebhookEndpoint, options_dict: dict | None) -> dict:
    """Convert a WebhookEndpoint + options to a dict matching WebhookRead."""
    data = {
        "id": webhook.id,
        "name": webhook.name,
        "url": webhook.url,
        "headers": webhook.headers,
        "webhook_type": webhook.webhook_type,
        "source_filters": webhook.source_filters,
        "options": options_dict,
        "enabled": webhook.enabled,
        "consecutive_failures": webhook.consecutive_failures,
        "created_at": webhook.created_at,
        "updated_at": webhook.updated_at,
    }
    return data


def _get_options_dict(session, webhook_id: UUID) -> dict | None:
    """Load WebhookOptions for an endpoint, returning the options dict or None."""
    opts = session.exec(
        select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == webhook_id)
    ).first()
    return opts.options if opts else None


@router.get(
    "",
    response_model=list[WebhookRead],
    summary="List webhook endpoints",
)
async def list_webhooks(
    session: SessionDep,
    auth: Annotated[tuple, Depends(require_role_or_api_key(ROLE_VIEWER))],
):
    """List all configured webhook endpoints."""
    statement = select(WebhookEndpoint).order_by(WebhookEndpoint.name)
    webhooks = session.exec(statement).all()

    # Batch load all options in a single query to avoid N+1
    webhook_ids = [wh.id for wh in webhooks]
    options_map: dict[UUID, dict] = {}
    if webhook_ids:
        all_opts = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id.in_(webhook_ids)  # type: ignore[attr-defined]
            )
        ).all()
        options_map = {opt.webhook_endpoint_id: opt.options for opt in all_opts}

    return [_webhook_to_read(wh, options_map.get(wh.id)) for wh in webhooks]


@router.post(
    "",
    response_model=WebhookRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a webhook endpoint",
)
async def create_webhook(
    data: WebhookCreate,
    session: SessionDep,
    auth: Annotated[tuple, Depends(require_role_or_api_key(ROLE_OPERATOR))],
):
    """Create a new webhook endpoint for failure notifications."""
    webhook = WebhookEndpoint(
        name=data.name,
        url=data.url,
        headers=data.headers,
        webhook_type=data.webhook_type,
        source_filters=data.source_filters,
        enabled=data.enabled,
    )
    session.add(webhook)
    session.commit()
    session.refresh(webhook)

    # Create WebhookOptions if options provided
    options_dict = None
    if data.options is not None:
        opts = WebhookOptions(
            webhook_endpoint_id=webhook.id,
            options=data.options,
        )
        session.add(opts)
        session.commit()
        session.refresh(opts)
        options_dict = opts.options

    logger.info(
        "Webhook created",
        extra={"webhook_name": data.name, "webhook_url": data.url},
    )
    return _webhook_to_read(webhook, options_dict)


@router.put(
    "/{webhook_id}",
    response_model=WebhookRead,
    summary="Update a webhook endpoint",
)
async def update_webhook(
    webhook_id: UUID,
    data: WebhookUpdate,
    session: SessionDep,
    auth: Annotated[tuple, Depends(require_role_or_api_key(ROLE_OPERATOR))],
):
    """Update an existing webhook endpoint."""
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Handle options separately
    options_data = update_data.pop("options", None)

    for key, value in update_data.items():
        setattr(webhook, key, value)
    webhook.updated_at = utc_now()

    session.add(webhook)
    session.commit()
    session.refresh(webhook)

    # Update or create WebhookOptions if options provided
    if options_data is not None:
        existing_opts = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id == webhook_id
            )
        ).first()

        if existing_opts:
            existing_opts.options = options_data
            existing_opts.updated_at = utc_now()
            session.add(existing_opts)
        else:
            new_opts = WebhookOptions(
                webhook_endpoint_id=webhook_id,
                options=options_data,
            )
            session.add(new_opts)
        session.commit()

    options_dict = _get_options_dict(session, webhook_id)

    logger.info("Webhook updated", extra={"webhook_id": str(webhook_id)})
    return _webhook_to_read(webhook, options_dict)


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook endpoint",
)
async def delete_webhook(
    webhook_id: UUID,
    session: SessionDep,
    auth: Annotated[tuple, Depends(require_role_or_api_key(ROLE_OPERATOR))],
):
    """Delete a webhook endpoint."""
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # CASCADE on FK will automatically delete associated WebhookOptions
    session.delete(webhook)
    session.commit()

    logger.info("Webhook deleted", extra={"webhook_id": str(webhook_id)})


@router.post(
    "/{webhook_id}/test",
    summary="Send a test notification",
)
async def test_webhook(
    webhook_id: UUID,
    session: SessionDep,
    auth: Annotated[tuple, Depends(require_role_or_api_key(ROLE_OPERATOR))],
):
    """Send a test notification to a webhook endpoint."""
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # Build test payload via shared service (AC-009)
    opts = get_webhook_options(session, webhook_id)
    payload = build_test_webhook_payload(webhook, opts)
    headers = build_test_headers(webhook)

    try:
        response = await send_test_webhook(webhook, payload, headers)
        if 200 <= response.status_code < 300:
            return {"status": "sent", "http_status": response.status_code}

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Webhook returned HTTP {response.status_code}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to deliver: {str(e)}",
        )
