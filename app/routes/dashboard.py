import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session, select, func

from app.database import get_session
from app.templating import templates
from app.models.failure_event import FailureEvent
from app.models.webhook import WebhookEndpoint
from app.models.notification_log import NotificationLog

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/htmx/notifications")
async def htmx_notifications(
    request: Request,
    session: Session = Depends(get_session),
    status: Optional[str] = Query(None),
    webhook_name: Optional[str] = Query(None),
    source_name: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """HTMX partial: notification history list with filters and pagination."""

    # Parse date params (AC-016)
    parsed_date_from = None
    parsed_date_to = None
    if date_from:
        try:
            parsed_date_from = datetime.strptime(date_from, "%Y-%m-%d")
        except ValueError:
            pass
    if date_to:
        try:
            parsed_date_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            pass

    # Build base query
    statement = select(NotificationLog)

    # Apply date filters (AC-016)
    if parsed_date_from:
        statement = statement.where(
            NotificationLog.created_at >= parsed_date_from  # type: ignore[arg-type]
        )
    if parsed_date_to:
        statement = statement.where(
            NotificationLog.created_at < parsed_date_to  # type: ignore[arg-type]
        )

    # Apply filters
    if status:
        statement = statement.where(NotificationLog.status == status)

    # For webhook_name and source_name filters, we need to join related tables
    if webhook_name:
        statement = statement.join(  # type: ignore[arg-type]
            WebhookEndpoint,
            NotificationLog.webhook_endpoint_id == WebhookEndpoint.id,  # type: ignore[arg-type]
        ).where(WebhookEndpoint.name == webhook_name)

    if source_name:
        statement = statement.join(  # type: ignore[arg-type]
            FailureEvent,
            NotificationLog.failure_event_id == FailureEvent.id,  # type: ignore[arg-type]
        ).where(FailureEvent.source_name == source_name)

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())  # type: ignore[attr-defined]
    total = session.exec(count_statement).one()

    # Apply ordering and pagination
    statement = (
        statement.order_by(NotificationLog.created_at.desc())  # type: ignore[attr-defined]
        .offset(offset)
        .limit(limit)
    )
    notifications = session.exec(statement).all()

    # Batch load related records to avoid N+1
    webhook_ids = {n.webhook_endpoint_id for n in notifications}
    failure_event_ids = {n.failure_event_id for n in notifications}

    webhooks_map: dict = {}
    if webhook_ids:
        wh_list = session.exec(
            select(WebhookEndpoint).where(WebhookEndpoint.id.in_(webhook_ids))  # type: ignore[attr-defined]
        ).all()
        webhooks_map = {wh.id: wh for wh in wh_list}

    events_map: dict = {}
    if failure_event_ids:
        fe_list = session.exec(
            select(FailureEvent).where(FailureEvent.id.in_(failure_event_ids))  # type: ignore[attr-defined]
        ).all()
        events_map = {fe.id: fe for fe in fe_list}

    # Get unique webhook names and source names for filter dropdowns
    all_webhook_names = session.exec(
        select(WebhookEndpoint.name).distinct().order_by(WebhookEndpoint.name)
    ).all()
    all_source_names = session.exec(
        select(FailureEvent.source_name).distinct().order_by(FailureEvent.source_name)
    ).all()

    return templates.TemplateResponse(
        request,
        "partials/notifications_list.html",
        context={
            "notifications": notifications,
            "webhooks_map": webhooks_map,
            "events_map": events_map,
            "total": total,
            "offset": offset,
            "limit": limit,
            "selected_status": status or "",
            "selected_webhook_name": webhook_name or "",
            "selected_source_name": source_name or "",
            "date_from": date_from or "",
            "date_to": date_to or "",
            "webhook_names": all_webhook_names,
            "source_names": all_source_names,
        },
    )
