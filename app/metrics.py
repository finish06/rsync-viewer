"""Prometheus metrics definitions and instrumentation."""

import time

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Use a custom registry to avoid test pollution from default registry
registry = CollectorRegistry()

# --- Sync metrics (AC-002) ---

syncs_total = Counter(
    "rsync_syncs_total",
    "Total number of rsync sync events processed",
    ["source", "status"],
    registry=registry,
)

sync_duration_seconds = Histogram(
    "rsync_sync_duration_seconds",
    "Duration of rsync sync operations",
    ["source"],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600, float("inf")],
    registry=registry,
)

files_transferred_total = Counter(
    "rsync_files_transferred_total",
    "Total files transferred across all syncs",
    ["source"],
    registry=registry,
)

bytes_transferred_total = Counter(
    "rsync_bytes_transferred_total",
    "Total bytes transferred across all syncs",
    ["source"],
    registry=registry,
)

# --- API metrics (AC-003) ---

api_requests_total = Counter(
    "rsync_api_requests_total",
    "Total API requests",
    ["endpoint", "method", "status"],
    registry=registry,
)

api_request_duration_seconds = Histogram(
    "rsync_api_request_duration_seconds",
    "API request duration",
    ["endpoint", "method"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float("inf")],
    registry=registry,
)

# --- Health metrics (AC-004) ---

app_info = Gauge(
    "rsync_app_info",
    "Application information",
    ["version"],
    registry=registry,
)


def set_app_info(version: str) -> None:
    """Set the application version info gauge."""
    app_info.labels(version=version).set(1)


def record_sync(
    source: str,
    status: str,
    duration_seconds: float | None = None,
    files: int | None = None,
    bytes_transferred: int | None = None,
) -> None:
    """Record metrics for a processed sync log."""
    syncs_total.labels(source=source, status=status).inc()
    if duration_seconds is not None and duration_seconds > 0:
        sync_duration_seconds.labels(source=source).observe(duration_seconds)
    if files is not None and files > 0:
        files_transferred_total.labels(source=source).inc(files)
    if bytes_transferred is not None and bytes_transferred > 0:
        bytes_transferred_total.labels(source=source).inc(bytes_transferred)


def get_metrics_output() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest(registry)


# Paths to exclude from API metrics tracking
METRICS_EXCLUDE_PATHS = {"/metrics", "/static"}


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Track API request counts and durations."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Don't track /metrics or /static
        if any(path.startswith(p) for p in METRICS_EXCLUDE_PATHS):
            return await call_next(request)  # type: ignore[no-any-return,return-value]

        method = request.method
        start = time.monotonic()

        response: Response = await call_next(request)

        duration = time.monotonic() - start
        status_code = str(response.status_code)

        api_requests_total.labels(
            endpoint=path, method=method, status=status_code
        ).inc()
        api_request_duration_seconds.labels(endpoint=path, method=method).observe(
            duration
        )

        return response
