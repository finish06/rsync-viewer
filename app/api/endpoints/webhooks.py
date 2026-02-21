"""Webhook endpoints CRUD API — placeholder for GREEN phase."""

import logging

from fastapi import APIRouter

from app.api.deps import SessionDep, ApiKeyDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
