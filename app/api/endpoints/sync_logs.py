from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select, func

from app.api.deps import SessionDep, ApiKeyDep
from app.models.sync_log import SyncLog
from app.schemas.sync_log import (
    SyncLogCreate,
    SyncLogRead,
    SyncLogDetail,
    SyncLogList,
    PaginatedResponse,
    SourceListResponse,
    ErrorResponse,
)
from app.services.rsync_parser import RsyncParser

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
    api_key: ApiKeyDep,
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
    )

    session.add(sync_log)
    session.commit()
    session.refresh(sync_log)

    return sync_log


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List sync logs",
    responses={
        200: {"description": "List of sync logs with pagination"},
    },
)
async def list_sync_logs(
    session: SessionDep,
    source_name: Optional[str] = Query(None, description="Filter by source name"),
    start_date: Optional[datetime] = Query(None, description="Filter syncs after this date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter syncs before this date (ISO 8601)"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
):
    """
    List sync logs with optional filtering and pagination.

    Results are ordered by start time (most recent first).
    """
    # Build query
    statement = select(SyncLog)

    if source_name:
        statement = statement.where(SyncLog.source_name == source_name)
    if start_date:
        statement = statement.where(SyncLog.start_time >= start_date)
    if end_date:
        statement = statement.where(SyncLog.start_time <= end_date)

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    # Apply pagination and ordering
    statement = statement.order_by(SyncLog.start_time.desc()).offset(offset).limit(limit)
    sync_logs = session.exec(statement).all()

    return PaginatedResponse(
        items=[SyncLogList.model_validate(log) for log in sync_logs],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/sources",
    response_model=SourceListResponse,
    summary="List sync sources",
    responses={
        200: {"description": "List of unique source names"},
    },
)
async def list_sources(session: SessionDep):
    """
    List all unique source names that have submitted sync logs.

    Useful for populating filter dropdowns in the UI.
    """
    statement = select(SyncLog.source_name).distinct().order_by(SyncLog.source_name)
    sources = session.exec(statement).all()
    return SourceListResponse(sources=sources)


@router.get(
    "/{sync_id}",
    response_model=SyncLogDetail,
    summary="Get sync log details",
    responses={
        200: {"description": "Sync log details including raw content and file list"},
        404: {"model": ErrorResponse, "description": "Sync log not found"},
    },
)
async def get_sync_log(sync_id: UUID, session: SessionDep):
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
