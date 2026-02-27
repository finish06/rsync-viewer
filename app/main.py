import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import UUID

import asyncio

import httpx
from fastapi import FastAPI, HTTPException, Request, Query, Depends
from starlette.responses import Response as StarletteResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlmodel import SQLModel, Session, select, func

from app.config import get_settings
from app.database import engine, get_session
from app.api.deps import OptionalUserDep
from app.api.endpoints import (
    sync_logs,
    monitors,
    failures,
    webhooks,
    analytics,
    auth,
    api_keys,
    users,
)
from app.errors import make_error_response, INTERNAL_ERROR, VALIDATION_ERROR
from app.logging_config import setup_logging
from app.metrics import PrometheusMiddleware, get_metrics_output, set_app_info
from app.middleware import (
    AuthRedirectMiddleware,
    BodySizeLimitMiddleware,
    CsrfMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.models.sync_log import SyncLog
from app.models.user import User  # noqa: F401 — ensure table creation
from app.models.user import RefreshToken  # noqa: F401 — ensure table creation
from app.models.user import PasswordResetToken  # noqa: F401 — ensure table creation
from app.models.smtp_config import SmtpConfig  # noqa: F401 — ensure table creation
from app.schemas.user import UserCreate
from app.services.auth import (
    create_access_token,
    hash_password,
    verify_password,
    ROLE_ADMIN,
    ROLE_VIEWER,
)
from app.services.changelog_parser import parse_changelog
from app.models.monitor import SyncSourceMonitor  # noqa: F401 — ensure table creation
from app.models.failure_event import FailureEvent
from app.models.webhook import WebhookEndpoint
from app.models.notification_log import NotificationLog
from app.models.webhook_options import WebhookOptions
from app.utils import utc_now

logger = logging.getLogger(__name__)

DISCORD_URL_PATTERN = re.compile(
    r"^https://(discord\.com|discordapp\.com)/api/webhooks/\d+/.+"
)


def _form_str(form: object, key: str, default: str = "") -> str:
    """Extract a string value from form data, handling UploadFile edge cases."""
    value = getattr(form, "get", lambda k, d: d)(key, default)
    return str(value) if value is not None else default


settings = get_settings()


def _get_rate_limit_key(request: Request) -> str:
    """Rate limit key: API key if present, else client IP."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[settings.rate_limit_authenticated],
    headers_enabled=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging on startup
    setup_logging(log_level=settings.log_level, log_format=settings.log_format)
    # Create tables on startup
    SQLModel.metadata.create_all(engine)

    # Set Prometheus app info
    set_app_info(version="1.5.0")

    # Start retention background task
    shutdown_event = asyncio.Event()
    retention_task = None
    if settings.data_retention_days > 0:
        from app.services.retention import retention_background_task

        retention_task = asyncio.create_task(
            retention_background_task(
                retention_days=settings.data_retention_days,
                interval_hours=settings.retention_cleanup_interval_hours,
                shutdown_event=shutdown_event,
                engine=engine,
            )
        )

    yield

    # Shutdown retention task
    shutdown_event.set()
    if retention_task is not None:
        retention_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.app_name,
    description="""
Rsync Log Viewer API collects, parses, and provides access to rsync synchronization logs.

## Features

- **Log Ingestion**: Submit raw rsync output for automatic parsing
- **Query Logs**: Filter and paginate through sync history
- **Statistics**: View transfer stats, file counts, and speeds

## Authentication

Protected endpoints require an API key passed via the `X-API-Key` header.
    """,
    version="1.5.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "sync-logs",
            "description": "Operations for managing rsync synchronization logs",
        },
    ],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Wrap HTTPExceptions in structured error format."""
    # Map detail messages to error codes
    detail = str(exc.detail)
    if "API key required" in detail:
        error_code = "API_KEY_REQUIRED"
    elif "Invalid or inactive API key" in detail:
        error_code = "API_KEY_INVALID"
    elif "not found" in detail.lower():
        error_code = "RESOURCE_NOT_FOUND"
    else:
        error_code = "BAD_REQUEST"

    return JSONResponse(
        status_code=exc.status_code,
        content=make_error_response(
            error_code=error_code,
            message=detail,
            path=str(request.url.path),
            detail=detail,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Wrap validation errors in structured error format."""
    return JSONResponse(
        status_code=422,
        content=make_error_response(
            error_code=VALIDATION_ERROR,
            message="Request validation failed",
            path=str(request.url.path),
            detail="One or more fields failed validation",
            validation_errors=[
                {
                    "loc": list(err.get("loc", [])),
                    "msg": err.get("msg", ""),
                    "type": err.get("type", ""),
                }
                for err in exc.errors()
            ],
        ),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions — no stack traces leaked."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=make_error_response(
            error_code=INTERNAL_ERROR,
            message="An internal server error occurred",
            path=str(request.url.path),
        ),
    )


# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Middleware order: outermost runs first
# SecurityHeaders → BodySizeLimit → Prometheus → RequestLogging → AuthRedirect → CSRF → (rate limiting)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(AuthRedirectMiddleware)
app.add_middleware(CsrfMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["app_version"] = settings.app_version


# Add custom template filters
def format_bytes(value: Optional[int]) -> str:
    """Format bytes to human readable format"""
    if value is None:
        return "-"
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(value) < 1024.0:
            return f"{value:.2f} {unit}"
        value = int(value / 1024.0)
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


def format_rate(sync) -> str:
    """Format average transfer rate from a sync log object."""
    if sync.is_dry_run:
        return "-"
    if sync.bytes_received is None:
        return "-"
    if not sync.start_time or not sync.end_time:
        return "-"
    duration_seconds = (sync.end_time - sync.start_time).total_seconds()
    if duration_seconds <= 0:
        return "-"
    rate = sync.bytes_received / duration_seconds
    for unit in ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"]:
        if abs(rate) < 1024.0:
            return f"{rate:.2f} {unit}"
        rate /= 1024.0
    return f"{rate:.2f} PB/s"


templates.env.filters["format_bytes"] = format_bytes
templates.env.filters["format_duration"] = format_duration
templates.env.filters["format_rate"] = format_rate


# Include API routers
app.include_router(sync_logs.router, prefix="/api/v1")
app.include_router(monitors.router, prefix="/api/v1")
app.include_router(failures.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.get("/")
async def index(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """Main dashboard page"""

    # Get unique sources for filter dropdown
    sources = session.exec(
        select(SyncLog.source_name).distinct().order_by(SyncLog.source_name)
    ).all()

    return templates.TemplateResponse(
        request,
        "index.html",
        context={"sources": sources, "user": user},
    )


@app.get("/analytics")
async def analytics_page():
    """Redirect to dashboard analytics tab."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/?tab=analytics", status_code=302)


def _parse_date(value: str) -> datetime:
    """Parse an ISO format date string, raising HTTPException on failure."""
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {value}",
        )


@app.get("/htmx/sync-table")
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

    # Build query
    statement = select(SyncLog)

    if source_name:
        statement = statement.where(SyncLog.source_name == source_name)
    if start_date:
        statement = statement.where(SyncLog.start_time >= _parse_date(start_date))
    if end_date:
        statement = statement.where(SyncLog.start_time <= _parse_date(end_date))

    # Filter dry runs
    if show_dry_run == "hide":
        statement = statement.where(SyncLog.is_dry_run.is_(False))  # type: ignore[attr-defined]
    elif show_dry_run == "only":
        statement = statement.where(SyncLog.is_dry_run.is_(True))  # type: ignore[attr-defined]

    # Filter empty runs (runs with zero files transferred)
    if hide_empty == "hide":
        statement = statement.where(SyncLog.file_count > 0)  # type: ignore[operator]
    elif hide_empty == "only":
        statement = statement.where(
            (SyncLog.file_count == 0) | (SyncLog.file_count == None)  # noqa: E711
        )

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    # Apply pagination and ordering
    if load_all:
        statement = statement.order_by(SyncLog.start_time.desc())  # type: ignore[attr-defined]
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


@app.get("/htmx/analytics")
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
        statement = statement.where(SyncLog.start_time >= _parse_date(start_date))
    if end_date:
        statement = statement.where(SyncLog.start_time <= _parse_date(end_date))

    # Filter dry runs
    if show_dry_run == "hide":
        statement = statement.where(SyncLog.is_dry_run.is_(False))  # type: ignore[attr-defined]
    elif show_dry_run == "only":
        statement = statement.where(SyncLog.is_dry_run.is_(True))  # type: ignore[attr-defined]

    # Filter empty runs
    if hide_empty == "hide":
        statement = statement.where(SyncLog.file_count > 0)  # type: ignore[operator]
    elif hide_empty == "only":
        statement = statement.where(
            (SyncLog.file_count == 0) | (SyncLog.file_count == None)  # noqa: E711
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


@app.get("/htmx/sync-detail/{sync_id}")
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


@app.get("/htmx/notifications")
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
    count_statement = select(func.count()).select_from(statement.subquery())
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


@app.get("/login")
async def login_page(
    request: Request,
    return_url: Optional[str] = Query(None),
    success: Optional[str] = Query(None),
):
    """Render login page."""
    from app.csrf import generate_csrf_token

    csrf_token = generate_csrf_token()
    success_message = None
    if success == "registered":
        success_message = "Account created successfully. Please log in."

    response = templates.TemplateResponse(
        request,
        "login.html",
        context={
            "csrf_token": csrf_token,
            "return_url": return_url or "",
            "success_message": success_message,
        },
    )
    response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="lax")
    return response


@app.post("/login")
async def login_submit(
    request: Request,
    session: Session = Depends(get_session),
):
    """Handle login form submission. Set JWT in httpOnly cookie."""
    from app.csrf import generate_csrf_token

    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    return_url = str(form.get("return_url", "/")).strip() or "/"

    # Validate credentials
    user = session.exec(select(User).where(User.username == username)).first()

    if not user or not verify_password(password, user.password_hash):
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse(
            request,
            "login.html",
            context={
                "csrf_token": csrf_token,
                "return_url": return_url,
                "error_message": "Invalid username or password",
            },
            status_code=401,
        )
        response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="lax")
        return response

    if not user.is_active:
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse(
            request,
            "login.html",
            context={
                "csrf_token": csrf_token,
                "return_url": return_url,
                "error_message": "Account is disabled",
            },
            status_code=403,
        )
        response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="lax")
        return response

    # Generate JWT
    access_token = create_access_token(user.id, user.username, user.role)

    # Update last login
    user.last_login_at = utc_now()
    session.add(user)
    session.commit()

    # Redirect to return_url with JWT in cookie
    from fastapi.responses import RedirectResponse

    redirect = RedirectResponse(url=return_url, status_code=302)
    redirect.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        samesite="lax",
        max_age=settings.jwt_access_expiry_minutes * 60,
    )
    return redirect


@app.post("/logout")
async def logout():
    """Clear access token cookie and redirect to login."""
    from fastapi.responses import RedirectResponse

    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@app.get("/register")
async def register_page(request: Request):
    """Render registration page."""
    settings = get_settings()
    if not settings.registration_enabled:
        return templates.TemplateResponse(
            request,
            "register.html",
            context={"registration_disabled": True},
        )

    from app.csrf import generate_csrf_token

    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse(
        request,
        "register.html",
        context={"csrf_token": csrf_token},
    )
    response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="lax")
    return response


@app.post("/register")
async def register_submit(
    request: Request,
    session: Session = Depends(get_session),
):
    """Handle registration form submission."""
    settings = get_settings()
    if not settings.registration_enabled:
        return templates.TemplateResponse(
            request,
            "register.html",
            context={"registration_disabled": True},
            status_code=403,
        )

    from app.csrf import generate_csrf_token

    form_data = await request.form()
    username = str(form_data.get("username", "")).strip()
    email = str(form_data.get("email", "")).strip()
    password = str(form_data.get("password", ""))

    # Validate via Pydantic schema
    try:
        user_data = UserCreate(username=username, email=email, password=password)
    except Exception as e:
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse(
            request,
            "register.html",
            context={
                "csrf_token": csrf_token,
                "error_message": str(e).split("\n")[0]
                if str(e)
                else "Validation error",
                "form_username": username,
                "form_email": email,
            },
            status_code=422,
        )
        response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="lax")
        return response

    # Check duplicates
    existing_username = session.exec(
        select(User).where(User.username == user_data.username)
    ).first()
    if existing_username:
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse(
            request,
            "register.html",
            context={
                "csrf_token": csrf_token,
                "error_message": "Username already exists",
                "form_username": username,
                "form_email": email,
            },
            status_code=409,
        )
        response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="lax")
        return response

    existing_email = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    if existing_email:
        csrf_token = generate_csrf_token()
        response = templates.TemplateResponse(
            request,
            "register.html",
            context={
                "csrf_token": csrf_token,
                "error_message": "Email already exists",
                "form_username": username,
                "form_email": email,
            },
            status_code=409,
        )
        response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="lax")
        return response

    # Create user
    user_count = session.exec(select(func.count()).select_from(User)).one()
    role = ROLE_ADMIN if user_count == 0 else ROLE_VIEWER

    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=role,
    )
    session.add(user)
    session.commit()

    logger.info(
        "User registered via UI",
        extra={"user_id": str(user.id), "username": user.username, "role": user.role},
    )

    # Redirect to login with success message
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/login?success=registered", status_code=302)


@app.get("/settings")
async def settings_page(request: Request, user: OptionalUserDep = None):
    """Settings page — requires Operator+ role."""
    from app.services.auth import role_at_least, ROLE_OPERATOR

    if user and not role_at_least(user.role, ROLE_OPERATOR):
        raise HTTPException(status_code=403, detail="Requires operator role")
    changelog_versions = parse_changelog(path=Path("CHANGELOG.md"))
    return templates.TemplateResponse(
        request,
        "settings.html",
        context={"changelog_available": len(changelog_versions) > 0, "user": user},
    )


@app.get("/htmx/changelog")
async def htmx_changelog_list(request: Request):
    """HTMX partial: changelog version accordion list."""
    versions = [
        v
        for v in parse_changelog(path=Path("CHANGELOG.md"))
        if v.version != "Unreleased"
    ]
    current_settings = get_settings()
    return templates.TemplateResponse(
        request,
        "partials/changelog_list.html",
        context={
            "versions": versions,
            "app_version": current_settings.app_version,
        },
    )


@app.get("/htmx/changelog/{version}")
async def htmx_changelog_detail(request: Request, version: str):
    """HTMX partial: expanded version content with grouped sections."""
    versions = parse_changelog(path=Path("CHANGELOG.md"))
    target = next((v for v in versions if v.version == version), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")
    return templates.TemplateResponse(
        request,
        "partials/changelog_detail.html",
        context={"version": target},
    )


# --- SMTP Settings HTMX routes ---


@app.get("/htmx/smtp-settings")
async def htmx_smtp_settings(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: SMTP configuration form."""
    from app.services.auth import ROLE_ADMIN, role_at_least
    from app.services.email import get_smtp_config

    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    config = get_smtp_config(session)
    has_encryption_key = bool(get_settings().smtp_encryption_key)

    return templates.TemplateResponse(
        request,
        "partials/smtp_settings.html",
        context={
            "smtp": config,
            "has_encryption_key": has_encryption_key,
        },
    )


@app.post("/htmx/smtp-settings")
async def htmx_smtp_settings_save(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: Save SMTP configuration."""
    from app.services.auth import ROLE_ADMIN, role_at_least
    from app.services.email import encrypt_password, get_smtp_config

    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    if not get_settings().smtp_encryption_key:
        return HTMLResponse(
            '<div class="auth-error">SMTP_ENCRYPTION_KEY is not set. '
            "Configure it in your .env file before saving SMTP settings.</div>",
            status_code=400,
        )

    form = await request.form()
    host = str(form.get("host", "")).strip()
    port_str = str(form.get("port", "")).strip()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    encryption = str(form.get("encryption", "starttls")).strip()
    from_address = str(form.get("from_address", "")).strip()
    from_name = str(form.get("from_name", "")).strip() or "Rsync Viewer"

    # Validate required fields
    if not host or not port_str or not from_address:
        return HTMLResponse(
            '<div class="auth-error">Host, port, and from address are required.</div>',
            status_code=422,
        )

    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError()
    except ValueError:
        return HTMLResponse(
            '<div class="auth-error">Port must be a number between 1 and 65535.</div>',
            status_code=422,
        )

    if encryption not in ("none", "starttls", "ssl_tls"):
        return HTMLResponse(
            '<div class="auth-error">Invalid encryption method.</div>',
            status_code=422,
        )

    config = get_smtp_config(session)
    if config is None:
        config = SmtpConfig(
            host=host,
            port=port,
            username=username or None,
            encryption=encryption,
            from_address=from_address,
            from_name=from_name,
            configured_by_id=user.id,
        )
    else:
        config.host = host
        config.port = port
        config.username = username or None
        config.encryption = encryption
        config.from_address = from_address
        config.from_name = from_name
        config.configured_by_id = user.id
        config.updated_at = utc_now()

    # Only update password if a new one was provided
    if password:
        config.encrypted_password = encrypt_password(password)

    session.add(config)
    session.commit()
    session.refresh(config)

    logger.info(
        "SMTP configuration saved",
        extra={"user_id": str(user.id), "host": host},
    )

    return templates.TemplateResponse(
        request,
        "partials/smtp_settings.html",
        context={
            "smtp": config,
            "has_encryption_key": True,
            "success_message": "SMTP configuration saved.",
        },
    )


@app.post("/htmx/smtp-settings/test")
async def htmx_smtp_test_email(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: Send a test email."""
    from app.services.auth import ROLE_ADMIN, role_at_least
    from app.services.email import send_test_email

    if not user or not role_at_least(user.role, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Admin only")

    form = await request.form()
    test_email = str(form.get("test_email", "")).strip()
    if not test_email:
        return HTMLResponse(
            '<div class="auth-error">Please enter a test email address.</div>',
            status_code=422,
        )

    try:
        send_test_email(session, to_address=test_email)
        return HTMLResponse(
            f'<div class="settings-success">Test email sent successfully to {test_email}.</div>'
        )
    except ValueError as e:
        return HTMLResponse(
            f'<div class="auth-error">{e}</div>',
            status_code=400,
        )
    except Exception as e:
        error_msg = str(e)
        logger.error("SMTP test email failed", extra={"error": error_msg})
        # Show a generic message to avoid leaking server internals
        return HTMLResponse(
            '<div class="auth-error">Test email failed: could not connect to SMTP server. Check logs for details.</div>',
            status_code=500,
        )


# --- API Key HTMX routes ---


@app.get("/htmx/api-keys")
async def htmx_api_keys_list(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: API keys list table."""
    from app.models.sync_log import ApiKey as ApiKeyModel

    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    statement = (
        select(ApiKeyModel)
        .where(
            ApiKeyModel.is_active.is_(True),  # type: ignore[attr-defined]
            ApiKeyModel.user_id == user.id,
        )
        .order_by(ApiKeyModel.created_at.desc())
    )  # type: ignore[attr-defined]
    api_keys = session.exec(statement).all()

    return templates.TemplateResponse(
        request,
        "partials/api_keys_list.html",
        context={"api_keys": api_keys, "user": user},
    )


@app.get("/htmx/api-keys/add")
async def htmx_api_key_add_form(
    request: Request,
    user: OptionalUserDep = None,
):
    """HTMX partial: API key creation form modal."""
    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    return templates.TemplateResponse(
        request,
        "partials/api_key_form.html",
        context={"user_role": user.role, "user": user},
    )


@app.post("/htmx/api-keys")
async def htmx_api_key_create(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: create a new API key and show the raw key once."""
    import secrets as secrets_module
    from app.api.deps import hash_api_key as _hash_api_key
    from app.models.sync_log import ApiKey as ApiKeyModel
    from app.services.auth import role_at_least as _role_at_least

    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    form = await request.form()
    name = str(form.get("name", "")).strip()
    role_override = str(form.get("role_override", "")).strip() or None

    if not name:
        return templates.TemplateResponse(
            request,
            "partials/api_key_form.html",
            context={
                "user_role": user.role,
                "user": user,
                "error": "Name is required.",
            },
        )

    # Validate role override
    effective_role = user.role
    if role_override:
        if not _role_at_least(user.role, role_override):
            return templates.TemplateResponse(
                request,
                "partials/api_key_form.html",
                context={
                    "user_role": user.role,
                    "user": user,
                    "error": f"Cannot create key with role '{role_override}'.",
                },
            )
        effective_role = role_override

    raw_key = "rsv_" + secrets_module.token_urlsafe(32)
    key_hash = _hash_api_key(raw_key)

    api_key = ApiKeyModel(
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        name=name,
        is_active=True,
        user_id=user.id,
        role_override=role_override,
        created_at=utc_now(),
    )
    session.add(api_key)
    session.commit()

    return templates.TemplateResponse(
        request,
        "partials/api_key_created.html",
        context={
            "key_name": name,
            "raw_key": raw_key,
            "effective_role": effective_role,
            "user": user,
        },
    )


@app.delete("/htmx/api-keys/{key_id}")
async def htmx_api_key_revoke(
    request: Request,
    key_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: revoke an API key and return updated list."""
    from app.models.sync_log import ApiKey as ApiKeyModel

    if not user:
        raise HTTPException(status_code=403, detail="Not authenticated")

    api_key = session.get(ApiKeyModel, key_id)
    if not api_key or not api_key.is_active or api_key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    session.add(api_key)
    session.commit()

    # Return updated list
    statement = (
        select(ApiKeyModel)
        .where(
            ApiKeyModel.is_active.is_(True),  # type: ignore[attr-defined]
            ApiKeyModel.user_id == user.id,
        )
        .order_by(ApiKeyModel.created_at.desc())
    )  # type: ignore[attr-defined]
    api_keys = session.exec(statement).all()

    return templates.TemplateResponse(
        request,
        "partials/api_keys_list.html",
        context={"api_keys": api_keys, "user": user},
    )


@app.get("/htmx/webhooks")
async def htmx_webhooks_list(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: webhook list table."""
    webhooks_list = session.exec(
        select(WebhookEndpoint).order_by(WebhookEndpoint.name)
    ).all()

    # Batch load options to avoid N+1
    webhook_ids = [wh.id for wh in webhooks_list]
    options_map: dict = {}
    if webhook_ids:
        all_opts = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id.in_(webhook_ids)  # type: ignore[attr-defined]
            )
        ).all()
        options_map = {opt.webhook_endpoint_id: opt.options for opt in all_opts}

    return templates.TemplateResponse(
        request,
        "partials/webhooks_list.html",
        context={
            "webhooks": webhooks_list,
            "options_map": options_map,
        },
    )


@app.get("/htmx/webhooks/add")
async def htmx_webhook_add_form(request: Request):
    """HTMX partial: empty webhook add form."""
    return templates.TemplateResponse(
        request,
        "partials/webhook_form.html",
        context={"webhook": None, "options": None, "errors": {}},
    )


@app.post("/htmx/webhooks")
async def htmx_webhook_create(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: create a new webhook endpoint. Requires Operator+ role."""
    from app.services.auth import role_at_least, ROLE_OPERATOR as _OP

    if not user or not role_at_least(user.role, _OP):
        raise HTTPException(status_code=403, detail="Requires operator role")
    form = await request.form()
    errors: dict[str, str] = {}

    name = _form_str(form, "name").strip()
    url = _form_str(form, "url").strip()
    webhook_type = _form_str(form, "webhook_type", "generic")
    source_filters_raw = _form_str(form, "source_filters").strip()
    headers_raw = _form_str(form, "headers").strip()
    enabled = _form_str(form, "enabled") == "on"

    # Validation
    if not name:
        errors["name"] = "Name is required."
    if not url:
        errors["url"] = "URL is required."
    elif webhook_type == "discord" and not DISCORD_URL_PATTERN.match(url):
        errors["url"] = (
            "Discord webhooks require a URL matching "
            "https://discord.com/api/webhooks/... or "
            "https://discordapp.com/api/webhooks/..."
        )

    headers = None
    if headers_raw:
        try:
            headers = json.loads(headers_raw)
        except json.JSONDecodeError:
            errors["headers"] = "Headers must be valid JSON."

    if errors:
        return templates.TemplateResponse(
            request,
            "partials/webhook_form.html",
            context={
                "webhook": None,
                "options": None,
                "errors": errors,
                "form": form,
            },
        )

    source_filters = (
        [s.strip() for s in source_filters_raw.split(",") if s.strip()]
        if source_filters_raw
        else None
    )

    webhook = WebhookEndpoint(
        name=name,
        url=url,
        headers=headers,
        webhook_type=webhook_type,
        source_filters=source_filters,
        enabled=enabled,
    )
    session.add(webhook)
    session.flush()  # Assigns webhook.id without committing

    # Create options for Discord webhooks
    if webhook_type == "discord":
        color_raw = _form_str(form, "discord_color", "#FF0045").strip()
        try:
            color_int = int(color_raw.lstrip("#"), 16)
        except ValueError:
            color_int = 16711749
        opts: dict[str, object] = {
            "color": color_int,
            "username": _form_str(form, "discord_username", "Rsync Viewer").strip()
            or "Rsync Viewer",
        }
        avatar_url_val = _form_str(form, "discord_avatar_url").strip()
        if avatar_url_val:
            opts["avatar_url"] = avatar_url_val
        footer = _form_str(form, "discord_footer").strip()
        if footer:
            opts["footer"] = footer

        wh_opts = WebhookOptions(webhook_endpoint_id=webhook.id, options=opts)
        session.add(wh_opts)

    session.commit()

    logger.info("Webhook created via UI", extra={"webhook_name": name})

    # Return updated list with closeModal trigger
    response = await htmx_webhooks_list(request, session)
    response.headers["HX-Trigger"] = "closeModal"
    return response


@app.get("/htmx/webhooks/{webhook_id}/edit")
async def htmx_webhook_edit_form(
    request: Request, webhook_id: UUID, session: Session = Depends(get_session)
):
    """HTMX partial: pre-filled webhook edit form."""
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        return HTMLResponse("<p>Webhook not found.</p>", status_code=404)

    opts_row = session.exec(
        select(WebhookOptions).where(WebhookOptions.webhook_endpoint_id == webhook_id)
    ).first()
    options = opts_row.options if opts_row else None

    return templates.TemplateResponse(
        request,
        "partials/webhook_form.html",
        context={"webhook": webhook, "options": options, "errors": {}},
    )


@app.put("/htmx/webhooks/{webhook_id}")
async def htmx_webhook_update(
    request: Request,
    webhook_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: update an existing webhook endpoint. Requires Operator+ role."""
    from app.services.auth import role_at_least, ROLE_OPERATOR as _OP

    if not user or not role_at_least(user.role, _OP):
        raise HTTPException(status_code=403, detail="Requires operator role")
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        return HTMLResponse("<p>Webhook not found.</p>", status_code=404)

    form = await request.form()
    errors: dict[str, str] = {}

    name = _form_str(form, "name").strip()
    url = _form_str(form, "url").strip()
    webhook_type = _form_str(form, "webhook_type", "generic")
    source_filters_raw = _form_str(form, "source_filters").strip()
    headers_raw = _form_str(form, "headers").strip()
    enabled = _form_str(form, "enabled") == "on"

    if not name:
        errors["name"] = "Name is required."
    if not url:
        errors["url"] = "URL is required."
    elif webhook_type == "discord" and not DISCORD_URL_PATTERN.match(url):
        errors["url"] = (
            "Discord webhooks require a URL matching "
            "https://discord.com/api/webhooks/... or "
            "https://discordapp.com/api/webhooks/..."
        )

    headers = None
    if headers_raw:
        try:
            headers = json.loads(headers_raw)
        except json.JSONDecodeError:
            errors["headers"] = "Headers must be valid JSON."

    if errors:
        # Reload options for re-rendering the form
        opts_row = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id == webhook_id
            )
        ).first()
        return templates.TemplateResponse(
            request,
            "partials/webhook_form.html",
            context={
                "webhook": webhook,
                "options": opts_row.options if opts_row else None,
                "errors": errors,
                "form": form,
            },
        )

    source_filters = (
        [s.strip() for s in source_filters_raw.split(",") if s.strip()]
        if source_filters_raw
        else None
    )

    webhook.name = name
    webhook.url = url
    webhook.headers = headers
    webhook.webhook_type = webhook_type
    webhook.source_filters = source_filters
    webhook.enabled = enabled
    webhook.updated_at = utc_now()
    session.add(webhook)

    # Update or create Discord options
    if webhook_type == "discord":
        color_raw = _form_str(form, "discord_color", "#FF0045").strip()
        try:
            color_int = int(color_raw.lstrip("#"), 16)
        except ValueError:
            color_int = 16711749
        opts: dict[str, object] = {
            "color": color_int,
            "username": _form_str(form, "discord_username", "Rsync Viewer").strip()
            or "Rsync Viewer",
        }
        avatar_url_val = _form_str(form, "discord_avatar_url").strip()
        if avatar_url_val:
            opts["avatar_url"] = avatar_url_val
        footer = _form_str(form, "discord_footer").strip()
        if footer:
            opts["footer"] = footer

        existing_opts = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id == webhook_id
            )
        ).first()
        if existing_opts:
            existing_opts.options = opts
            existing_opts.updated_at = utc_now()
            session.add(existing_opts)
        else:
            new_opts = WebhookOptions(webhook_endpoint_id=webhook_id, options=opts)
            session.add(new_opts)
    else:
        # Remove options if switching away from Discord
        existing_opts = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id == webhook_id
            )
        ).first()
        if existing_opts:
            session.delete(existing_opts)

    session.commit()

    logger.info("Webhook updated via UI", extra={"webhook_id": str(webhook_id)})

    response = await htmx_webhooks_list(request, session)
    response.headers["HX-Trigger"] = "closeModal"
    return response


@app.delete("/htmx/webhooks/{webhook_id}")
async def htmx_webhook_delete(
    request: Request,
    webhook_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: delete a webhook endpoint. Requires Operator+ role."""
    from app.services.auth import role_at_least, ROLE_OPERATOR as _OP

    if not user or not role_at_least(user.role, _OP):
        raise HTTPException(status_code=403, detail="Requires operator role")
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        return HTMLResponse("<p>Webhook not found.</p>", status_code=404)

    session.delete(webhook)
    session.commit()

    logger.info("Webhook deleted via UI", extra={"webhook_id": str(webhook_id)})

    return await htmx_webhooks_list(request, session)


@app.post("/htmx/webhooks/{webhook_id}/toggle")
async def htmx_webhook_toggle(
    request: Request,
    webhook_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: toggle webhook enabled/disabled. Requires Operator+ role."""
    from app.services.auth import role_at_least, ROLE_OPERATOR as _OP

    if not user or not role_at_least(user.role, _OP):
        raise HTTPException(status_code=403, detail="Requires operator role")
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        return HTMLResponse("<p>Webhook not found.</p>", status_code=404)

    webhook.enabled = not webhook.enabled
    webhook.updated_at = utc_now()
    session.add(webhook)
    session.commit()

    return await htmx_webhooks_list(request, session)


@app.post("/htmx/webhooks/{webhook_id}/test")
async def htmx_webhook_test(
    request: Request,
    webhook_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: send a test notification. Requires Operator+ role."""
    from app.services.auth import role_at_least, ROLE_OPERATOR as _OP

    if not user or not role_at_least(user.role, _OP):
        raise HTTPException(status_code=403, detail="Requires operator role")
    webhook = session.get(WebhookEndpoint, webhook_id)
    if not webhook:
        return HTMLResponse("<p>Webhook not found.</p>", status_code=404)

    # Build test payload based on webhook type
    if webhook.webhook_type == "discord":
        opts_row = session.exec(
            select(WebhookOptions).where(
                WebhookOptions.webhook_endpoint_id == webhook_id
            )
        ).first()
        opts = opts_row.options if opts_row else {}
        color = opts.get("color", 16711680)
        username = opts.get("username", "Rsync Viewer")
        payload = {
            "username": username,
            "embeds": [
                {
                    "title": "Test Notification",
                    "description": "This is a test notification from Rsync Viewer.",
                    "color": color,
                }
            ],
        }
        if opts.get("avatar_url"):
            payload["avatar_url"] = opts["avatar_url"]
    else:
        payload = {
            "event": "test",
            "message": "This is a test notification from Rsync Viewer.",
        }

    req_headers = {"Content-Type": "application/json"}
    if webhook.headers:
        req_headers.update(webhook.headers)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook.url,
                json=payload,
                headers=req_headers,
                timeout=10.0,
            )
        if 200 <= response.status_code < 300:
            return HTMLResponse(
                '<span class="test-result test-success">Test sent successfully!</span>'
            )
        return HTMLResponse(
            f'<span class="test-result test-failure">Failed: HTTP {response.status_code}</span>'
        )
    except httpx.RequestError as e:
        return HTMLResponse(
            f'<span class="test-result test-failure">Failed: {e}</span>'
        )


# ── Admin User Management UI ──────────────────────────────────────────


@app.get("/admin/users")
async def admin_users_page(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """Render admin user management page (admin only)."""
    from app.services.auth import role_at_least, ROLE_ADMIN as _ADMIN

    if not user or not role_at_least(user.role, _ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    users_list = session.exec(select(User).order_by(User.created_at.desc())).all()
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        context={"users": users_list, "user": user, "current_user": user},
    )


@app.get("/htmx/admin/users")
async def htmx_admin_user_list(
    request: Request,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX partial: admin user list table."""
    from app.services.auth import role_at_least, ROLE_ADMIN as _ADMIN

    if not user or not role_at_least(user.role, _ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    users_list = session.exec(select(User).order_by(User.created_at.desc())).all()
    return templates.TemplateResponse(
        request,
        "partials/admin_user_list.html",
        context={"users": users_list, "current_user": user},
    )


@app.put("/htmx/admin/users/{user_id}/role")
async def htmx_admin_change_role(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: change a user's role."""
    from app.services.auth import role_at_least, ROLE_ADMIN as _ADMIN, VALID_ROLES

    if not user or not role_at_least(user.role, _ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    form = await request.form()
    new_role = str(form.get("role", "")).strip()

    if new_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {new_role}")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.role == "admin" and new_role != "admin":
        admin_count = session.exec(
            select(func.count()).where(User.role == "admin", User.is_active.is_(True))
        ).one()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin")

    target.role = new_role
    session.add(target)
    session.commit()

    return await htmx_admin_user_list(request, session, user)


@app.put("/htmx/admin/users/{user_id}/toggle-status")
async def htmx_admin_toggle_status(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: toggle user active status."""
    from app.services.auth import role_at_least, ROLE_ADMIN as _ADMIN

    if not user or not role_at_least(user.role, _ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own status")

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_active = not target.is_active
    session.add(target)
    session.commit()

    return await htmx_admin_user_list(request, session, user)


@app.delete("/htmx/admin/users/{user_id}")
async def htmx_admin_delete_user(
    request: Request,
    user_id: UUID,
    session: Session = Depends(get_session),
    user: OptionalUserDep = None,
):
    """HTMX: delete a user."""
    from app.services.auth import role_at_least, ROLE_ADMIN as _ADMIN

    if not user or not role_at_least(user.role, _ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    target = session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.role == "admin":
        admin_count = session.exec(
            select(func.count()).where(User.role == "admin", User.is_active.is_(True))
        ).one()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin")

    session.delete(target)
    session.commit()

    return await htmx_admin_user_list(request, session, user)


# ── Password Reset UI Pages ──────────────────────────────────────────


@app.get("/forgot-password")
async def forgot_password_page(request: Request):
    """Render forgot password page."""
    from app.csrf import generate_csrf_token

    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse(
        request,
        "forgot_password.html",
        context={"csrf_token": csrf_token},
    )
    response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="lax")
    return response


@app.get("/reset-password")
async def reset_password_page(
    request: Request,
    token: Optional[str] = Query(None),
):
    """Render reset password page."""
    from app.csrf import generate_csrf_token

    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse(
        request,
        "reset_password.html",
        context={"csrf_token": csrf_token, "token": token or ""},
    )
    response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="lax")
    return response


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint (AC-001, AC-009).

    Unauthenticated — standard for Prometheus scraping.
    """
    data = get_metrics_output()
    return StarletteResponse(
        content=data,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}
