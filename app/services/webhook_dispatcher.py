"""Webhook dispatcher service — dispatches failure notifications to configured webhook endpoints."""

import asyncio
import logging

import httpx
from sqlmodel import Session

from app.models.failure_event import FailureEvent

logger = logging.getLogger(__name__)


async def dispatch_webhooks(session: Session, event: FailureEvent) -> None:
    """Dispatch webhook notifications for a failure event.

    This is a placeholder — will be implemented in GREEN phase.
    """
    raise NotImplementedError("Webhook dispatcher not yet implemented")
