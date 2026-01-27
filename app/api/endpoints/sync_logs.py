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
)
from app.services.rsync_parser import RsyncParser

router = APIRouter(prefix="/sync-logs", tags=["sync-logs"])


@router.post("", response_model=SyncLogRead, status_code=status.HTTP_201_CREATED)
async def create_sync_log(
    data: SyncLogCreate,
    session: SessionDep,
    api_key: ApiKeyDep,
):
    """Create a new sync log entry"""
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


@router.get("", response_model=PaginatedResponse)
async def list_sync_logs(
    session: SessionDep,
    source_name: Optional[str] = Query(None, description="Filter by source name"),
    start_date: Optional[datetime] = Query(None, description="Filter syncs after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter syncs before this date"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
):
    """List sync logs with optional filtering"""
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


@router.get("/sources", response_model=SourceListResponse)
async def list_sources(session: SessionDep):
    """List unique source names"""
    statement = select(SyncLog.source_name).distinct().order_by(SyncLog.source_name)
    sources = session.exec(statement).all()
    return SourceListResponse(sources=sources)


@router.get("/{sync_id}", response_model=SyncLogDetail)
async def get_sync_log(sync_id: UUID, session: SessionDep):
    """Get a single sync log by ID"""
    sync_log = session.get(SyncLog, sync_id)
    if not sync_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sync log not found",
        )
    return sync_log
