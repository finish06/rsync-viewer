import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import Response as StarletteResponse
from app.config import get_settings
from app.database import engine
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
from app.services.retention import retention_background_task
from app.services.synthetic_check import synthetic_check_background_task
from app.services.sync_filters import InvalidDateError

# Model imports — ensure SQLModel tables are created
from app.models.sync_log import SyncLog, ApiKey  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user import RefreshToken  # noqa: F401
from app.models.user import PasswordResetToken  # noqa: F401
from app.models.smtp_config import SmtpConfig  # noqa: F401
from app.models.monitor import SyncSourceMonitor  # noqa: F401
from app.models.failure_event import FailureEvent  # noqa: F401
from app.models.webhook import WebhookEndpoint  # noqa: F401
from app.models.notification_log import NotificationLog  # noqa: F401
from app.models.webhook_options import WebhookOptions  # noqa: F401
from app.models.oidc_config import OidcConfig  # noqa: F401

# HTMX route modules
from app.routes import (
    pages,
    auth as htmx_auth,
    dashboard,
    settings,
    api_keys as htmx_api_keys,
    webhooks as htmx_webhooks,
    admin,
)  # noqa: E501

# Backward-compat re-exports — tests import these from app.main
from app.templating import (  # noqa: F401
    templates,
    format_bytes,
    format_duration,
    format_rate,
    _form_str,
    DISCORD_URL_PATTERN,
)

logger = logging.getLogger(__name__)

settings_cfg = get_settings()


def _get_rate_limit_key(request: Request) -> str:
    """Rate limit key: API key if present, else client IP."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[settings_cfg.rate_limit_authenticated],
    headers_enabled=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging on startup
    setup_logging(log_level=settings_cfg.log_level, log_format=settings_cfg.log_format)
    # Database migrations are handled by entrypoint.sh (alembic upgrade head)
    # before the application starts. No create_all() needed.

    # Set Prometheus app info
    set_app_info(version=settings_cfg.app_version)

    # Start retention background task
    shutdown_event = asyncio.Event()
    retention_task = None
    if settings_cfg.data_retention_days > 0:
        retention_task = asyncio.create_task(
            retention_background_task(
                retention_days=settings_cfg.data_retention_days,
                interval_hours=settings_cfg.retention_cleanup_interval_hours,
                shutdown_event=shutdown_event,
                engine=engine,
            )
        )

    # Start synthetic monitoring background task (AC-001, AC-012)
    synthetic_task = None
    if settings_cfg.synthetic_check_enabled:
        synthetic_api_key = (
            settings_cfg.synthetic_check_api_key or settings_cfg.default_api_key
        )
        if not settings_cfg.debug and not settings_cfg.synthetic_check_api_key:
            logger.warning(
                "Synthetic monitoring is enabled but SYNTHETIC_CHECK_API_KEY is not set "
                "and DEBUG is false. The default API key will not work in production. "
                "Set SYNTHETIC_CHECK_API_KEY to a provisioned key in the api_keys table."
            )
        synthetic_task = asyncio.create_task(
            synthetic_check_background_task(
                enabled=True,
                interval_seconds=settings_cfg.synthetic_check_interval_seconds,
                shutdown_event=shutdown_event,
                base_url="http://127.0.0.1:8000",
                api_key=synthetic_api_key,
                engine=engine,
            )
        )

    yield

    # Shutdown background tasks
    shutdown_event.set()
    for task in (retention_task, synthetic_task):
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title=settings_cfg.app_name,
    description="""
Rsync Log Viewer API collects, parses, and provides access to rsync synchronization logs.

## Features

- **Log Ingestion**: Submit raw rsync output for automatic parsing
- **Query Logs**: Filter and paginate through sync history
- **Statistics**: View transfer stats, file counts, and speeds

## Authentication

Protected endpoints require an API key passed via the `X-API-Key` header.
    """,
    version=settings_cfg.app_version,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "sync-logs",
            "description": "Operations for managing rsync synchronization logs",
        },
    ],
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Wrap HTTPExceptions in structured error format."""
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


@app.exception_handler(InvalidDateError)
async def invalid_date_handler(request: Request, exc: InvalidDateError):
    """Return 400 for unparseable date query parameters."""
    return JSONResponse(
        status_code=400,
        content=make_error_response(
            error_code=VALIDATION_ERROR,
            message=str(exc),
            path=str(request.url.path),
        ),
    )


# ---------------------------------------------------------------------------
# Middleware (outermost runs first)
# ---------------------------------------------------------------------------

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(AuthRedirectMiddleware)
app.add_middleware(CsrfMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

# REST API routers
app.include_router(sync_logs.router, prefix="/api/v1")
app.include_router(monitors.router, prefix="/api/v1")
app.include_router(failures.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")

# HTMX / UI route modules (AC-001, AC-002)
app.include_router(pages.router)
app.include_router(htmx_auth.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(htmx_api_keys.router)
app.include_router(htmx_webhooks.router)
app.include_router(admin.router)


# ---------------------------------------------------------------------------
# Infrastructure endpoints
# ---------------------------------------------------------------------------


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
    """Health check endpoint (AC-009: includes synthetic check status)."""
    from app.services.synthetic_check import get_state

    state = get_state()
    synthetic_check = None
    if state.enabled:
        synthetic_check = {
            "status": state.last_status,
            "last_check_at": (
                state.last_check_at.isoformat() if state.last_check_at else None
            ),
            "last_latency_ms": state.last_latency_ms,
        }

    return {"status": "ok", "synthetic_check": synthetic_check}
