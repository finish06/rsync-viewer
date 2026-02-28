import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session, select, func

from app.database import get_session
from app.api.deps import OptionalUserDep
from app.templating import templates, format_bytes, format_duration
from app.models.sync_log import SyncLog
from app.models.failure_event import FailureEvent
from app.models.webhook import WebhookEndpoint
from app.models.notification_log import NotificationLog
from app.services.sync_filters import apply_sync_filters

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/htmx/sync-table")
async def htmx_sync_table(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
    source_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    show_dry_run: str = Query("hide"),
    hide_empty: str = Query("hide"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    load_all: bool = Query(False),
):
    """HTMX partial: sync logs table"""

    # Build query with shared filter helper (AC-007)
    statement = apply_sync_filters(
        select(SyncLog),
        source_name=source_name,
        start_date=start_date,
        end_date=end_date,
        show_dry_run=show_dry_run,
        hide_empty=hide_empty,
    )

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())  # type: ignore[attr-defined]
    total = session.exec(count_statement).one()

    # Apply pagination and ordering
    if load_all:
        statement = statement.order_by(SyncLog.start_time.desc()).limit(10000)  # type: ignore[attr-defined]
    else:
        statement = (
            statement.order_by(SyncLog.start_time.desc()).offset(offset).limit(limit)  # type: ignore[attr-defined]
        )
    syncs = session.exec(statement).all()

    # Get sources for filter
    sources = session.exec(
        select(SyncLog.source_name).distinct().order_by(SyncLog.source_name)
    ).all()

    return templates.TemplateResponse(
        request,
        "partials/sync_table.html",
        context={
            "syncs": syncs,
            "total": total,
            "offset": offset,
            "limit": limit,
            "load_all": load_all,
            "sources": sources,
            "selected_source": source_name,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "show_dry_run": show_dry_run,
            "hide_empty": hide_empty,
        },
    )


@router.get("/htmx/analytics")
async def htmx_analytics(request: Request, session: Session = Depends(get_session)):
    """HTMX partial: analytics tab with charts, comparison, and export."""
    sources = session.exec(
        select(SyncLog.source_name).distinct().order_by(SyncLog.source_name)
    ).all()

    return templates.TemplateResponse(
        request,
        "partials/analytics.html",
        context={"sources": sources},
    )


@router.get("/htmx/charts")
async def htmx_charts(
    request: Request,
    session: Session = Depends(get_session),
    source_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    show_dry_run: str = Query("hide"),
    hide_empty: str = Query("hide"),
):
    """HTMX partial: sync statistics charts"""

    # Build query with shared filter helper (AC-007)
    statement = apply_sync_filters(
        select(SyncLog),
        source_name=source_name,
        start_date=start_date,
        end_date=end_date,
        show_dry_run=show_dry_run,
        hide_empty=hide_empty,
    )

    # Get recent syncs (limit 50, ordered by time ascending for charts)
    statement = statement.order_by(SyncLog.start_time.desc()).limit(50)  # type: ignore[attr-defined]
    syncs = session.exec(statement).all()

    # Reverse to show oldest first in charts (left to right)
    syncs = list(reversed(syncs))

    # Prepare chart data
    chart_data: dict[str, list] = {
        "labels": [],
        "durations": [],
        "duration_labels": [],
        "file_counts": [],
        "bytes_transferred": [],
        "bytes_labels": [],
        "sources": [],
    }

    for sync in syncs:
        # Label: short date/time
        label = sync.start_time.strftime("%m/%d %H:%M") if sync.start_time else ""
        chart_data["labels"].append(label)
        chart_data["sources"].append(sync.source_name or "unknown")

        # Duration in seconds
        if sync.start_time and sync.end_time:
            duration = (sync.end_time - sync.start_time).total_seconds()
            chart_data["durations"].append(duration)
            chart_data["duration_labels"].append(
                format_duration(sync.end_time - sync.start_time)
            )
        else:
            chart_data["durations"].append(0)
            chart_data["duration_labels"].append("-")

        # File count
        chart_data["file_counts"].append(sync.file_count or 0)

        # Bytes transferred
        bytes_val = sync.bytes_received or 0
        chart_data["bytes_transferred"].append(bytes_val)
        chart_data["bytes_labels"].append(format_bytes(bytes_val))

    return templates.TemplateResponse(
        request,
        "partials/charts.html",
        context={
            "chart_data": chart_data,
            "has_data": len(syncs) > 0,
        },
    )


@router.get("/htmx/sync-detail/{sync_id}")
async def htmx_sync_detail(
    request: Request, sync_id: UUID, session: Session = Depends(get_session)
):
    """HTMX partial: sync log detail modal"""
    sync = session.get(SyncLog, sync_id)

    if not sync:
        return templates.TemplateResponse(
            request,
            "partials/not_found.html",
        )

    return templates.TemplateResponse(
        request,
        "partials/sync_detail.html",
        context={"sync": sync},
    )


@router.get("/htmx/notifications")
async def htmx_notifications(
    request: Request,
    session: Session = Depends(get_session),
    status: Optional[str] = Query(None),
    webhook_name: Optional[str] = Query(None),
    source_name: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """HTMX partial: notification history list with filters and pagination."""

    # Build base query
    statement = select(NotificationLog)

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
            "webhook_names": all_webhook_names,
            "source_names": all_source_names,
        },
    )
