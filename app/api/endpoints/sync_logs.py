import base64
import json
import logging
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import defer
from sqlmodel import select, func

from app.api.deps import SessionDep, AdminDep, require_role_or_api_key
from app.services.auth import ROLE_OPERATOR, ROLE_VIEWER
from app.models.sync_log import SyncLog
from app.models.failure_event import FailureEvent
from app.models.monitor import SyncSourceMonitor
from app.schemas.sync_log import (
    CursorPagination,
    SyncLogCreate,
    SyncLogRead,
    SyncLogDetail,
    SyncLogList,
    PaginatedResponse,
    SourceListResponse,
    ErrorResponse,
)
from app.metrics import record_sync
from app.services.rsync_parser import RsyncParser
from app.services.synthetic_check import SYNTHETIC_SOURCE_NAME
from app.services.webhook_dispatcher import dispatch_webhooks

logger = logging.getLogger(__name__)


def _encode_cursor(start_time: datetime, record_id: UUID) -> str:
    """Encode a cursor from start_time and id."""
    payload = {"t": start_time.isoformat(), "id": str(record_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decode a cursor into (start_time, id). Raises HTTPException on invalid cursor."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor))
        return datetime.fromisoformat(payload["t"]), UUID(payload["id"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cursor value",
        )


router = APIRouter(prefix="/sync-logs", tags=["sync-logs"])


@router.post(
    "",
    response_model=SyncLogRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a sync log",
    responses={
        201: {"description": "Sync log created successfully"},
        401: {"model": ErrorResponse, "description": "API key missing or invalid"},
        422: {"description": "Validation error in request body"},
    },
)
async def create_sync_log(
    data: SyncLogCreate,
    session: SessionDep,
    auth: Annotated[tuple, Depends(require_role_or_api_key(ROLE_OPERATOR))],
):
    """
    Create a new sync log entry by submitting raw rsync output.

    The raw content will be automatically parsed to extract:
    - Transfer statistics (bytes sent/received, speed)
    - Total size and speedup ratio
    - List of transferred files
    - Dry run detection

    **Authentication required**: Pass your API key via the `X-API-Key` header.
    """
    # Parse the raw content
    parsed = RsyncParser.parse(data.raw_content)

    # Create the sync log
    sync_log = SyncLog(
        source_name=data.source_name,
        start_time=data.start_time,
        end_time=data.end_time,
        raw_content=data.raw_content,
        total_size_bytes=parsed.total_size_bytes,
        bytes_sent=parsed.bytes_sent,
        bytes_received=parsed.bytes_received,
        transfer_speed=parsed.transfer_speed,
        speedup_ratio=parsed.speedup_ratio,
        file_count=parsed.file_count,
        file_list=parsed.file_list if parsed.file_list else None,
        is_dry_run=parsed.is_dry_run,
        exit_code=data.exit_code,
    )

    session.add(sync_log)
    session.commit()
    session.refresh(sync_log)

    # Record Prometheus metrics
    duration_seconds = None
    if sync_log.start_time and sync_log.end_time:
        duration_seconds = (sync_log.end_time - sync_log.start_time).total_seconds()
    record_sync(
        source=sync_log.source_name,
        status="failed" if (data.exit_code and data.exit_code != 0) else "success",
        duration_seconds=duration_seconds,
        files=sync_log.file_count,
        bytes_transferred=sync_log.bytes_received,
    )

    # Create FailureEvent for non-zero exit codes
    failure = None
    if data.exit_code is not None and data.exit_code != 0:
        failure = FailureEvent(
            source_name=data.source_name,
            failure_type="exit_code",
            sync_log_id=sync_log.id,
            details=f"rsync exited with code {data.exit_code}",
        )
        session.add(failure)

    # Update monitor's last_sync_at if a monitor exists for this source
    monitor = session.exec(
        select(SyncSourceMonitor).where(
            SyncSourceMonitor.source_name == data.source_name
        )
    ).first()
    if monitor:
        monitor.last_sync_at = sync_log.end_time
        session.add(monitor)

    # Single commit for failure event + monitor update
    if failure or monitor:
        session.commit()

    # Dispatch webhook notifications after commit (failure must be persisted)
    if failure:
        session.refresh(failure)
        await dispatch_webhooks(session, failure)

    logger.info(
        "Sync log created",
        extra={
            "source_name": data.source_name,
            "file_count": parsed.file_count,
            "is_dry_run": parsed.is_dry_run,
        },
    )

    return sync_log


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List sync logs",
    responses={
        200: {"description": "List of sync logs with pagination"},
        400: {"model": ErrorResponse, "description": "Invalid cursor value"},
    },
)
async def list_sync_logs(
    session: SessionDep,
    auth: Annotated[tuple, Depends(require_role_or_api_key(ROLE_VIEWER))],
    source_name: Optional[str] = Query(None, description="Filter by source name"),
    start_date: Optional[datetime] = Query(
        None, description="Filter syncs after this date (ISO 8601)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter syncs before this date (ISO 8601)"
    ),
    cursor: Optional[str] = Query(
        None, description="Opaque cursor for keyset pagination"
    ),
    direction: Optional[str] = Query(
        "forward",
        description="Pagination direction: 'forward' (default) or 'backward'",
    ),
    offset: Optional[int] = Query(
        None, ge=0, description="(Deprecated) Number of records to skip"
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of records to return"
    ),
    synthetic: str = Query(
        "hide",
        description="Synthetic log filter: 'hide' (default), 'only', or 'show'",
    ),
):
    """
    List sync logs with optional filtering and pagination.

    Supports cursor-based pagination (preferred) and offset pagination (deprecated).
    Results are ordered by start time (most recent first).

    **Cursor pagination:** Use the `cursor` parameter from the `pagination.next_cursor`
    or `pagination.prev_cursor` fields in the response. Set `direction=backward` to
    page backwards.

    **Offset pagination (deprecated):** Use the `offset` parameter for legacy clients.
    """
    # Determine pagination mode: cursor takes precedence, offset is fallback
    use_offset = cursor is None and offset is not None

    # Build base query with filters — defer heavy columns for list view
    statement = select(SyncLog).options(
        defer(SyncLog.raw_content), defer(SyncLog.file_list)
    )

    # Synthetic filter (AC-008)
    if synthetic == "hide":
        statement = statement.where(SyncLog.source_name != SYNTHETIC_SOURCE_NAME)
    elif synthetic == "only":
        statement = statement.where(SyncLog.source_name == SYNTHETIC_SOURCE_NAME)

    if synthetic != "only" and source_name:
        statement = statement.where(SyncLog.source_name == source_name)
    if start_date:
        statement = statement.where(SyncLog.start_time >= start_date)
    if end_date:
        statement = statement.where(SyncLog.start_time <= end_date)

    if use_offset:
        # Legacy offset pagination mode
        count_statement = select(func.count()).select_from(statement.subquery())
        total = session.exec(count_statement).one()

        statement = (
            statement.order_by(SyncLog.start_time.desc()).offset(offset).limit(limit)  # type: ignore[attr-defined]
        )
        sync_logs = session.exec(statement).all()

        return PaginatedResponse(
            items=[SyncLogList.model_validate(log) for log in sync_logs],
            total=total,
            offset=offset,
            limit=limit,
        )

    # Cursor-based pagination mode
    is_backward = direction == "backward"

    if cursor:
        cursor_time, cursor_id = _decode_cursor(cursor)
        if is_backward:
            # Going backward: get items NEWER than cursor (start_time > cursor)
            statement = statement.where(
                (SyncLog.start_time > cursor_time)  # type: ignore[operator]
                | (
                    (SyncLog.start_time == cursor_time)  # type: ignore[operator]
                    & (SyncLog.id > cursor_id)  # type: ignore[operator]
                )
            )
        else:
            # Going forward: get items OLDER than cursor (start_time < cursor)
            statement = statement.where(
                (SyncLog.start_time < cursor_time)  # type: ignore[operator]
                | (
                    (SyncLog.start_time == cursor_time)  # type: ignore[operator]
                    & (SyncLog.id < cursor_id)  # type: ignore[operator]
                )
            )

    if is_backward:
        # Fetch in ascending order then reverse for backward
        statement = statement.order_by(
            SyncLog.start_time.asc(),
            SyncLog.id.asc(),  # type: ignore[attr-defined]
        ).limit(limit + 1)
    else:
        statement = statement.order_by(
            SyncLog.start_time.desc(),
            SyncLog.id.desc(),  # type: ignore[attr-defined]
        ).limit(limit + 1)

    results = list(session.exec(statement).all())

    # Check if there are more results beyond our page
    has_more = len(results) > limit
    if has_more:
        results = results[:limit]

    if is_backward:
        results.reverse()

    # Build cursors
    next_cursor = None
    prev_cursor = None
    has_next = False
    has_prev = False

    if results:
        if is_backward:
            has_prev = has_more
            # Check if there are items after the last result (has_next)
            last = results[-1]
            check_next = select(func.count()).select_from(
                select(SyncLog.id)
                .where(
                    (SyncLog.start_time < last.start_time)  # type: ignore[operator]
                    | (
                        (SyncLog.start_time == last.start_time)  # type: ignore[operator]
                        & (SyncLog.id < last.id)  # type: ignore[operator]
                    )
                )
                .subquery()
            )
            # Apply original filters
            if source_name:
                check_next = select(func.count()).select_from(
                    select(SyncLog.id)
                    .where(SyncLog.source_name == source_name)
                    .where(
                        (SyncLog.start_time < last.start_time)  # type: ignore[operator]
                        | (
                            (SyncLog.start_time == last.start_time)  # type: ignore[operator]
                            & (SyncLog.id < last.id)  # type: ignore[operator]
                        )
                    )
                    .subquery()
                )
            has_next = session.exec(check_next).one() > 0
        else:
            has_next = has_more
            # has_prev is true if we have a cursor (we came from somewhere)
            has_prev = cursor is not None

        first = results[0]
        last = results[-1]
        next_cursor = _encode_cursor(last.start_time, last.id) if has_next else None
        prev_cursor = _encode_cursor(first.start_time, first.id) if has_prev else None

    return PaginatedResponse(
        items=[SyncLogList.model_validate(log) for log in results],
        pagination=CursorPagination(
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=has_next,
            has_prev=has_prev,
            limit=limit,
        ),
    )


@router.get(
    "/sources",
    response_model=SourceListResponse,
    summary="List sync sources",
    responses={
        200: {"description": "List of unique source names"},
    },
)
async def list_sources(
    session: SessionDep,
    auth: Annotated[tuple, Depends(require_role_or_api_key(ROLE_VIEWER))],
):
    """
    List all unique source names that have submitted sync logs.

    Useful for populating filter dropdowns in the UI.
    """
    statement = (
        select(SyncLog.source_name)
        .where(SyncLog.source_name != SYNTHETIC_SOURCE_NAME)
        .distinct()
        .order_by(SyncLog.source_name)
    )
    sources = session.exec(statement).all()
    return SourceListResponse(sources=list(sources))


@router.get(
    "/{sync_id}",
    response_model=SyncLogDetail,
    summary="Get sync log details",
    responses={
        200: {"description": "Sync log details including raw content and file list"},
        404: {"model": ErrorResponse, "description": "Sync log not found"},
    },
)
async def get_sync_log(
    sync_id: UUID,
    session: SessionDep,
    auth: Annotated[tuple, Depends(require_role_or_api_key(ROLE_VIEWER))],
):
    """
    Get detailed information about a specific sync log.

    Returns the full sync log including:
    - All parsed statistics
    - Raw rsync output
    - List of transferred files
    """
    sync_log = session.get(SyncLog, sync_id)
    if not sync_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sync log not found",
        )
    return sync_log


@router.delete(
    "/{sync_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a sync log",
    responses={
        204: {"description": "Sync log deleted successfully"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Sync log not found"},
    },
)
async def delete_sync_log(
    sync_id: UUID,
    session: SessionDep,
    user: AdminDep,
):
    """
    Delete a sync log entry. Requires Admin role.
    """
    sync_log = session.get(SyncLog, sync_id)
    if not sync_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sync log not found",
        )
    session.delete(sync_log)
    session.commit()
    logger.info(
        "Sync log deleted", extra={"sync_id": str(sync_id), "deleted_by": user.username}
    )
