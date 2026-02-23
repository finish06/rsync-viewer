"""Analytics and reporting API endpoints (specs/analytics.md)."""

import csv
import io
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import select, func, case, col, extract

from app.api.deps import SessionDep
from app.models.sync_log import SyncLog
from app.schemas.analytics import (
    ExportRecord,
    SourceStats,
    SummaryDataPoint,
    SummaryPeriod,
    SummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

MAX_EXPORT_LIMIT = 10000


def _date_trunc_expr(period: SummaryPeriod):
    """Return a SQL expression that truncates start_time to the given period."""
    if period == SummaryPeriod.daily:
        return func.date_trunc("day", SyncLog.start_time)
    elif period == SummaryPeriod.weekly:
        return func.date_trunc("week", SyncLog.start_time)
    else:
        return func.date_trunc("month", SyncLog.start_time)


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="Get aggregated sync statistics",
)
async def get_summary(
    session: SessionDep,
    period: SummaryPeriod = Query(..., description="Aggregation period"),
    start: date = Query(..., description="Start date (ISO 8601)"),
    end: date = Query(..., description="End date (ISO 8601)"),
    source: Optional[str] = Query(None, description="Filter by source name"),
):
    """AC-001, AC-003: Return daily/weekly/monthly summary with aggregated stats."""
    start_dt = datetime(start.year, start.month, start.day, 0, 0, 0)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59)

    trunc = _date_trunc_expr(period)

    # Duration in seconds: extract(epoch from end_time - start_time)
    duration_expr = extract("epoch", SyncLog.end_time - SyncLog.start_time)

    statement = (
        select(  # type: ignore[call-overload]
            trunc.label("period_start"),
            func.count().label("total_syncs"),
            func.sum(
                case((col(SyncLog.exit_code) == 0, 1), else_=0)
            ).label("successful_syncs"),
            func.sum(
                case(
                    (
                        (col(SyncLog.exit_code) != 0)
                        & (col(SyncLog.exit_code).is_not(None)),
                        1,
                    ),
                    else_=0,
                )
            ).label("failed_syncs"),
            func.avg(duration_expr).label("avg_duration"),
            func.coalesce(func.sum(SyncLog.bytes_received), 0).label("total_bytes"),
            func.coalesce(func.sum(SyncLog.file_count), 0).label("total_files"),
        )
        .where(SyncLog.start_time >= start_dt)
        .where(SyncLog.start_time <= end_dt)
        .group_by(trunc)
        .order_by(trunc)
    )

    if source:
        statement = statement.where(SyncLog.source_name == source)

    results = session.exec(statement).all()

    data = []
    for row in results:
        data.append(
            SummaryDataPoint(
                date=row.period_start.strftime("%Y-%m-%d"),
                total_syncs=row.total_syncs,
                successful_syncs=row.successful_syncs,
                failed_syncs=row.failed_syncs,
                avg_duration_seconds=(
                    round(row.avg_duration, 2) if row.avg_duration else None
                ),
                total_bytes_transferred=row.total_bytes,
                total_files_transferred=row.total_files,
            )
        )

    return SummaryResponse(
        period=period.value,
        start=start.isoformat(),
        end=end.isoformat(),
        data=data,
    )


@router.get(
    "/sources",
    response_model=list[SourceStats],
    summary="Get per-source aggregate statistics",
)
async def get_source_stats(
    session: SessionDep,
    start: Optional[date] = Query(None, description="Start date filter"),
    end: Optional[date] = Query(None, description="End date filter"),
):
    """AC-002: Return per-source stats (total syncs, success rate, avg duration, etc.)."""
    duration_expr = extract("epoch", SyncLog.end_time - SyncLog.start_time)

    statement = select(  # type: ignore[call-overload]
        SyncLog.source_name,
        func.count().label("total_syncs"),
        func.sum(
            case((col(SyncLog.exit_code) == 0, 1), else_=0)
        ).label("successful_syncs"),
        func.avg(duration_expr).label("avg_duration"),
        func.avg(SyncLog.file_count).label("avg_files"),
        func.avg(SyncLog.bytes_received).label("avg_bytes"),
        func.max(SyncLog.start_time).label("last_sync_at"),
    ).group_by(SyncLog.source_name)

    if start:
        start_dt = datetime(start.year, start.month, start.day, 0, 0, 0)
        statement = statement.where(SyncLog.start_time >= start_dt)
    if end:
        end_dt = datetime(end.year, end.month, end.day, 23, 59, 59)
        statement = statement.where(SyncLog.start_time <= end_dt)

    results = session.exec(statement).all()

    return [
        SourceStats(
            source_name=row.source_name,
            total_syncs=row.total_syncs,
            success_rate=(
                round(row.successful_syncs / row.total_syncs, 4)
                if row.total_syncs > 0
                else 0.0
            ),
            avg_duration_seconds=(
                round(row.avg_duration, 2) if row.avg_duration else None
            ),
            avg_files_transferred=(
                round(float(row.avg_files), 2) if row.avg_files is not None else None
            ),
            avg_bytes_transferred=(
                round(float(row.avg_bytes), 2) if row.avg_bytes is not None else None
            ),
            last_sync_at=row.last_sync_at,
        )
        for row in results
    ]


@router.get(
    "/export",
    summary="Export sync events in CSV or JSON format",
)
async def export_data(
    session: SessionDep,
    format: str = Query(..., description="Export format: csv or json"),
    start: Optional[date] = Query(None, description="Start date filter"),
    end: Optional[date] = Query(None, description="End date filter"),
    source: Optional[str] = Query(None, description="Filter by source name"),
    limit: int = Query(default=10000, ge=1, description="Max records"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
):
    """AC-004, AC-005, AC-010: Export sync events with filters and pagination."""
    if format not in ("csv", "json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format '{format}'. Use 'csv' or 'json'.",
        )

    # Cap limit at MAX_EXPORT_LIMIT
    effective_limit = min(limit, MAX_EXPORT_LIMIT)

    statement = select(  # type: ignore[call-overload,misc]
        SyncLog.source_name,
        SyncLog.start_time,
        SyncLog.end_time,
        SyncLog.file_count,
        SyncLog.bytes_received,
        SyncLog.bytes_sent,
        SyncLog.total_size_bytes,
        SyncLog.exit_code,
        SyncLog.status,
        SyncLog.is_dry_run,
    ).order_by(SyncLog.start_time.desc())

    if source:
        statement = statement.where(SyncLog.source_name == source)
    if start:
        start_dt = datetime(start.year, start.month, start.day, 0, 0, 0)
        statement = statement.where(SyncLog.start_time >= start_dt)
    if end:
        end_dt = datetime(end.year, end.month, end.day, 23, 59, 59)
        statement = statement.where(SyncLog.start_time <= end_dt)

    statement = statement.offset(offset).limit(effective_limit)
    results = session.exec(statement).all()

    records = [
        ExportRecord(
            source_name=r.source_name,
            start_time=r.start_time,
            end_time=r.end_time,
            duration_seconds=(
                (r.end_time - r.start_time).total_seconds()
                if r.end_time and r.start_time
                else None
            ),
            file_count=r.file_count,
            bytes_received=r.bytes_received,
            bytes_sent=r.bytes_sent,
            total_size_bytes=r.total_size_bytes,
            exit_code=r.exit_code,
            status=r.status,
            is_dry_run=r.is_dry_run,
        )
        for r in results  # type: ignore[union-attr]
    ]

    if format == "csv":
        return _csv_response(records)
    else:
        return _json_response(records)


def _csv_response(records: list[ExportRecord]) -> StreamingResponse:
    """Generate a CSV streaming response."""
    output = io.StringIO()
    fieldnames = [
        "source_name",
        "start_time",
        "end_time",
        "duration_seconds",
        "file_count",
        "bytes_received",
        "bytes_sent",
        "total_size_bytes",
        "exit_code",
        "status",
        "is_dry_run",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow(record.model_dump())

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sync_export.csv"},
    )


def _json_response(records: list[ExportRecord]) -> list[dict]:
    """Return JSON-serializable list of records."""
    return [
        {
            k: v.isoformat() if isinstance(v, datetime) else v
            for k, v in record.model_dump().items()
        }
        for record in records
    ]
