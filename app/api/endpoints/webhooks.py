import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import SessionDep, ApiKeyDep
from app.models.webhook import WebhookEndpoint
from app.schemas.webhook import WebhookCreate, WebhookUpdate, WebhookRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get(
    "",
    response_model=list[WebhookRead],
    summary="List webhook endpoints",
)
async def list_webhooks(session: SessionDep, api_key: ApiKeyDep):
    """List all configured webhook endpoints."""
    statement = select(WebhookEndpoint).order_by(WebhookEndpoint.name)
    webhooks = session.exec(statement).all()
    return webhooks


@router.post(
    "",
    response_model=WebhookRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a webhook endpoint",
)
async def create_webhook(
    data: WebhookCreate, session: SessionDep, api_key: ApiKeyDep
):
    """Create a new webhook endpoint for failure notifications."""
    webhook = WebhookEndpoint(
        name=data.name,
        url=data.url,
        headers=data.headers,
        enabled=data.enabled,
    )
    session.add(webhook)
    session.commit()
    session.refresh(webhook)

    logger.info(
        "Webhook created",
        extra={"webhook_name": data.name, "webhook_url": data.url},
    )
    return webhook


@router.put(
    "/{webhook_id}",
    response_model=WebhookRead,
    summary="Update a webhook endpoint",
)
async def update_webhook(
    webhook_id: UUID,
    data: WebhookUpdate,
    session: SessionDep,
    api_key: ApiKeyDep,
):
    """Update an existing webhook endpoint."""
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(webhook, key, value)
    webhook.updated_at = datetime.utcnow()

    session.add(webhook)
    session.commit()
    session.refresh(webhook)

    logger.info("Webhook updated", extra={"webhook_id": str(webhook_id)})
    return webhook


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook endpoint",
)
async def delete_webhook(
    webhook_id: UUID, session: SessionDep, api_key: ApiKeyDep
):
    """Delete a webhook endpoint."""
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    session.delete(webhook)
    session.commit()

    logger.info("Webhook deleted", extra={"webhook_id": str(webhook_id)})
