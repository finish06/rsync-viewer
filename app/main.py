from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, Request, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Session, select, func

from app.config import get_settings
from app.database import engine, get_session
from app.api.endpoints import sync_logs
from app.models.sync_log import SyncLog


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="app/templates")


# Add custom template filters
def format_bytes(value: Optional[int]) -> str:
    """Format bytes to human readable format"""
    if value is None:
        return "-"
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(value) < 1024.0:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"


def format_duration(delta: timedelta) -> str:
    """Format timedelta to human readable format"""
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")

    return " ".join(parts)


templates.env.filters["format_bytes"] = format_bytes
templates.env.filters["format_duration"] = format_duration


# Include API router
app.include_router(sync_logs.router, prefix="/api/v1")


@app.get("/")
async def index(request: Request, session: Session = Depends(get_session)):
    """Main dashboard page"""

    # Get unique sources for filter dropdown
    sources = session.exec(
        select(SyncLog.source_name).distinct().order_by(SyncLog.source_name)
    ).all()

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "sources": sources},
    )


@app.get("/htmx/sync-table")
async def htmx_sync_table(
    request: Request,
    session: Session = Depends(get_session),
    source_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    show_dry_run: str = Query("hide"),
    hide_empty: str = Query("hide"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """HTMX partial: sync logs table"""

    # Build query
    statement = select(SyncLog)

    if source_name:
        statement = statement.where(SyncLog.source_name == source_name)
    if start_date:
        statement = statement.where(SyncLog.start_time >= datetime.fromisoformat(start_date))
    if end_date:
        statement = statement.where(SyncLog.start_time <= datetime.fromisoformat(end_date))

    # Filter dry runs
    if show_dry_run == "hide":
        statement = statement.where(SyncLog.is_dry_run == False)
    elif show_dry_run == "only":
        statement = statement.where(SyncLog.is_dry_run == True)

    # Filter empty runs (runs with zero files transferred)
    if hide_empty == "hide":
        statement = statement.where(SyncLog.file_count > 0)
    elif hide_empty == "only":
        statement = statement.where((SyncLog.file_count == 0) | (SyncLog.file_count == None))

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    # Apply pagination and ordering
    statement = statement.order_by(SyncLog.start_time.desc()).offset(offset).limit(limit)
    syncs = session.exec(statement).all()

    # Get sources for filter
    sources = session.exec(
        select(SyncLog.source_name).distinct().order_by(SyncLog.source_name)
    ).all()

    return templates.TemplateResponse(
        "partials/sync_table.html",
        {
            "request": request,
            "syncs": syncs,
            "total": total,
            "offset": offset,
            "limit": limit,
            "sources": sources,
            "selected_source": source_name,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "show_dry_run": show_dry_run,
            "hide_empty": hide_empty,
        },
    )


@app.get("/htmx/charts")
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

    # Build query with same filters as sync-table
    statement = select(SyncLog)

    if source_name:
        statement = statement.where(SyncLog.source_name == source_name)
    if start_date:
        statement = statement.where(SyncLog.start_time >= datetime.fromisoformat(start_date))
    if end_date:
        statement = statement.where(SyncLog.start_time <= datetime.fromisoformat(end_date))

    # Filter dry runs
    if show_dry_run == "hide":
        statement = statement.where(SyncLog.is_dry_run == False)
    elif show_dry_run == "only":
        statement = statement.where(SyncLog.is_dry_run == True)

    # Filter empty runs
    if hide_empty == "hide":
        statement = statement.where(SyncLog.file_count > 0)
    elif hide_empty == "only":
        statement = statement.where((SyncLog.file_count == 0) | (SyncLog.file_count == None))

    # Get recent syncs (limit 50, ordered by time ascending for charts)
    statement = statement.order_by(SyncLog.start_time.desc()).limit(50)
    syncs = session.exec(statement).all()

    # Reverse to show oldest first in charts (left to right)
    syncs = list(reversed(syncs))

    # Prepare chart data
    chart_data = {
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
            chart_data["duration_labels"].append(format_duration(sync.end_time - sync.start_time))
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
        "partials/charts.html",
        {
            "request": request,
            "chart_data": chart_data,
            "has_data": len(syncs) > 0,
        },
    )


@app.get("/htmx/sync-detail/{sync_id}")
async def htmx_sync_detail(request: Request, sync_id: UUID, session: Session = Depends(get_session)):
    """HTMX partial: sync log detail modal"""
    sync = session.get(SyncLog, sync_id)

    if not sync:
        return templates.TemplateResponse(
            "partials/not_found.html",
            {"request": request},
        )

    return templates.TemplateResponse(
        "partials/sync_detail.html",
        {"request": request, "sync": sync},
    )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}
