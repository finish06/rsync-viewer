import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from sqlmodel import select

from app.api.deps import SessionDep, ApiKeyDep
from app.models.failure_event import FailureEvent
from app.schemas.failure_event import FailureEventRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/failures", tags=["failures"])


@router.get(
    "",
    response_model=list[FailureEventRead],
    summary="List failure events",
)
async def list_failures(
    session: SessionDep,
    api_key: ApiKeyDep,
    source_name: Optional[str] = Query(None, description="Filter by source name"),
    failure_type: Optional[str] = Query(None, description="Filter by failure type (exit_code or stale)"),
    since: Optional[datetime] = Query(None, description="Only failures after this time (ISO 8601)"),
    notified: Optional[bool] = Query(None, description="Filter by notification status"),
):
    """List failure events with optional filtering."""
    statement = select(FailureEvent)

    if source_name:
        statement = statement.where(FailureEvent.source_name == source_name)
    if failure_type:
        statement = statement.where(FailureEvent.failure_type == failure_type)
    if since:
        statement = statement.where(FailureEvent.detected_at >= since)
    if notified is not None:
        statement = statement.where(FailureEvent.notified == notified)

    statement = statement.order_by(FailureEvent.detected_at.desc())
    events = session.exec(statement).all()
    return events
