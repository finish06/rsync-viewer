"""Synthetic monitoring service.

Periodically POSTs a canned rsync log to the app's own API, verifies the
response, DELETEs it on success, and fires webhooks on failure.

v0.2.0 adds DB-backed config, runtime start/stop, and result storage.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

import httpx

if TYPE_CHECKING:
    from sqlmodel import Session

from app.metrics import synthetic_check_duration, synthetic_check_status
from app.models.failure_event import FailureEvent
from app.services.webhook_dispatcher import dispatch_webhooks
from app.utils import utc_now

logger = logging.getLogger(__name__)

SYNTHETIC_SOURCE_NAME = "__synthetic_check"

CANNED_RSYNC_LOG = """\
sending incremental file list
synthetic-test-file.txt
              100 100%    0.00kB/s    0:00:00 (xfr#1, to-chk=0/1)

Number of files: 1 (reg: 1)
Number of created files: 0
Number of deleted files: 0
Number of regular files transferred: 1
Total file size: 100 bytes
Total transferred file size: 100 bytes
Literal data: 100 bytes
Matched data: 0 bytes
File list size: 0
Total bytes sent: 150
Total bytes received: 35
sent 150 bytes  received 35 bytes  370.00 bytes/sec
total size is 100  speedup is 0.54"""

MINIMUM_INTERVAL_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 10.0
MAX_RESULT_ROWS = 100


@dataclass
class SyntheticCheckResult:
    """Result of a single synthetic check cycle."""

    status: str  # "passing" or "failing"
    latency_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class SyntheticCheckState:
    """In-memory state for the synthetic check service."""

    enabled: bool = False
    interval_seconds: int = 300
    last_status: str = "unknown"
    last_check_at: Optional[datetime] = None
    last_latency_ms: Optional[float] = None
    last_error: Optional[str] = None


# Module-level state — accessed by health endpoint and settings UI
_state = SyntheticCheckState()

# Module-level background task state for runtime start/stop (AC-013)
_background_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
_shutdown_event: Optional[asyncio.Event] = None


def get_state() -> SyntheticCheckState:
    """Return current synthetic check state."""
    return _state


# ---------------------------------------------------------------------------
# DB persistence helpers (AC-014, AC-016)
# ---------------------------------------------------------------------------


def get_db_config(session: "Session"):
    """Return the singleton config row, seeding from env vars if absent."""
    from sqlmodel import select

    from app.config import get_settings
    from app.models.synthetic_check_config import SyntheticCheckConfig

    row = session.exec(select(SyntheticCheckConfig)).first()
    if row is not None:
        return row

    # Seed from environment (bootstrap defaults)
    settings = get_settings()
    row = SyntheticCheckConfig(
        id=1,
        enabled=settings.synthetic_check_enabled,
        interval_seconds=settings.synthetic_check_interval_seconds,
        api_key=settings.synthetic_check_api_key or None,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def save_db_config(
    session: "Session",
    *,
    enabled: bool,
    interval_seconds: int,
):
    """Update the singleton config row."""
    config = get_db_config(session)
    config.enabled = enabled
    config.interval_seconds = max(interval_seconds, MINIMUM_INTERVAL_SECONDS)
    config.updated_at = utc_now()
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def store_check_result(
    session: "Session",
    outcome: SyntheticCheckResult,
) -> None:
    """Insert a check result row and prune to MAX_RESULT_ROWS."""
    from sqlmodel import col, select

    from app.models.synthetic_check_result import SyntheticCheckResultRecord

    record = SyntheticCheckResultRecord(
        checked_at=utc_now(),
        status=outcome.status,
        latency_ms=outcome.latency_ms,
        error=outcome.error,
    )
    session.add(record)
    session.flush()

    # Prune: keep only the newest MAX_RESULT_ROWS
    count_stmt = select(SyntheticCheckResultRecord.id).order_by(
        col(SyntheticCheckResultRecord.checked_at).desc()
    )
    all_ids = session.exec(count_stmt).all()
    if len(all_ids) > MAX_RESULT_ROWS:
        ids_to_delete = all_ids[MAX_RESULT_ROWS:]
        for old_id in ids_to_delete:
            old_row = session.get(SyntheticCheckResultRecord, old_id)
            if old_row:
                session.delete(old_row)

    session.commit()


def get_check_history(
    session: "Session",
    limit: int = 50,
) -> list:
    """Return the last N check results, newest first."""
    from sqlmodel import col, select

    from app.models.synthetic_check_result import SyntheticCheckResultRecord

    stmt = (
        select(SyntheticCheckResultRecord)
        .order_by(col(SyntheticCheckResultRecord.checked_at).desc())
        .limit(limit)
    )
    return list(session.exec(stmt).all())


def get_uptime_percentage(
    session: "Session",
    hours: int = 24,
) -> Optional[float]:
    """Return pass/total ratio over the given window. None if no data."""
    from sqlmodel import col, select

    from app.models.synthetic_check_result import SyntheticCheckResultRecord

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = select(SyntheticCheckResultRecord).where(
        col(SyntheticCheckResultRecord.checked_at) >= cutoff
    )
    results = list(session.exec(stmt).all())
    if not results:
        return None
    passing = sum(1 for r in results if r.status == "passing")
    return round((passing / len(results)) * 100, 1)


# ---------------------------------------------------------------------------
# Runtime start/stop (AC-013)
# ---------------------------------------------------------------------------


async def start_synthetic_monitoring(engine) -> None:
    """Stop any existing task, read DB config, start new task if enabled."""
    global _background_task, _shutdown_event

    await stop_synthetic_monitoring()

    from sqlmodel import Session as _Session

    from app.config import get_settings

    with _Session(engine) as session:
        config = get_db_config(session)
        if not config.enabled:
            _state.enabled = False
            logger.info("Synthetic monitoring disabled (DB config)")
            return

        settings = get_settings()
        api_key = (
            config.api_key
            or settings.synthetic_check_api_key
            or settings.default_api_key
        )

    _shutdown_event = asyncio.Event()
    _background_task = asyncio.create_task(
        synthetic_check_background_task(
            enabled=True,
            interval_seconds=config.interval_seconds,
            shutdown_event=_shutdown_event,
            base_url="http://127.0.0.1:8000",
            api_key=api_key,
            engine=engine,
        )
    )


async def stop_synthetic_monitoring() -> None:
    """Stop the running background task if any."""
    global _background_task, _shutdown_event

    if _shutdown_event is not None:
        _shutdown_event.set()

    if _background_task is not None:
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass

    _background_task = None
    _shutdown_event = None
    _state.enabled = False


# ---------------------------------------------------------------------------
# Core check logic
# ---------------------------------------------------------------------------


async def run_synthetic_check(
    *,
    base_url: str,
    api_key: str,
    db_session: "Optional[Session]" = None,
) -> SyntheticCheckResult:
    """Execute one synthetic check cycle: POST, verify, DELETE.

    Args:
        base_url: The base URL of the app's API (e.g. http://localhost:8000).
        api_key: API key to use for authentication.
        db_session: Optional DB session for webhook dispatch on failure.

    Returns:
        SyntheticCheckResult with status and latency.
    """
    start = time.monotonic()
    headers = {"X-API-Key": api_key}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            # Step 1: POST canned log
            post_response = await client.post(
                f"{base_url}/api/v1/sync-logs",
                json={
                    "source_name": SYNTHETIC_SOURCE_NAME,
                    "raw_content": CANNED_RSYNC_LOG,
                },
                headers=headers,
            )

            elapsed_ms = (time.monotonic() - start) * 1000

            if post_response.status_code != 201:
                error_msg = (
                    f"POST /api/v1/sync-logs returned {post_response.status_code}: "
                    f"{post_response.text[:200]}"
                )
                logger.error("Synthetic check FAILED", extra={"error": error_msg})

                # Record failing metrics
                synthetic_check_status.set(0)
                synthetic_check_duration.observe(elapsed_ms / 1000)

                # Fire webhook (AC-004)
                if db_session is not None:
                    event = FailureEvent(
                        source_name=SYNTHETIC_SOURCE_NAME,
                        failure_type="synthetic_failure",
                        details=error_msg,
                        detected_at=utc_now(),
                    )
                    db_session.add(event)
                    db_session.flush()
                    await dispatch_webhooks(db_session, event)

                result = SyntheticCheckResult(
                    status="failing",
                    latency_ms=elapsed_ms,
                    error=error_msg,
                )
                _update_state(result)
                return result

            # Verify response fields (AC-002)
            data = post_response.json()
            log_id = data.get("id")

            # Step 2: DELETE the created log (AC-003)
            if log_id:
                delete_response = await client.delete(
                    f"{base_url}/api/v1/sync-logs/{log_id}",
                    headers=headers,
                )
                if delete_response.status_code != 204:
                    logger.warning(
                        "Synthetic check DELETE failed (non-critical)",
                        extra={
                            "log_id": log_id,
                            "status_code": delete_response.status_code,
                        },
                    )

            # Record passing metrics
            synthetic_check_status.set(1)
            synthetic_check_duration.observe(elapsed_ms / 1000)

            logger.info(
                "Synthetic check passed",
                extra={"latency_ms": round(elapsed_ms, 1)},
            )

            result = SyntheticCheckResult(
                status="passing",
                latency_ms=elapsed_ms,
            )
            _update_state(result)
            return result

    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error("Synthetic check FAILED", extra={"error": error_msg})

        synthetic_check_status.set(0)
        synthetic_check_duration.observe(elapsed_ms / 1000)

        # Fire webhook on connection/timeout failures (AC-004)
        if db_session is not None:
            event = FailureEvent(
                source_name=SYNTHETIC_SOURCE_NAME,
                failure_type="synthetic_failure",
                details=error_msg,
                detected_at=utc_now(),
            )
            db_session.add(event)
            db_session.flush()
            await dispatch_webhooks(db_session, event)

        result = SyntheticCheckResult(
            status="failing",
            latency_ms=elapsed_ms,
            error=error_msg,
        )
        _update_state(result)
        return result


def _update_state(result: SyntheticCheckResult) -> None:
    """Update module-level in-memory state from a check result."""
    _state.last_status = result.status
    _state.last_check_at = utc_now()
    _state.last_latency_ms = result.latency_ms
    _state.last_error = result.error


async def synthetic_check_background_task(
    *,
    enabled: bool,
    interval_seconds: int,
    shutdown_event: asyncio.Event,
    base_url: str,
    api_key: str,
    engine=None,
) -> None:
    """Background task that periodically runs synthetic checks.

    Args:
        enabled: Whether synthetic checks are active.
        interval_seconds: Seconds between checks (clamped to minimum 30).
        shutdown_event: Event signaling app shutdown.
        base_url: App API base URL.
        api_key: API key for authentication.
        engine: SQLAlchemy engine for creating sessions (for webhook dispatch).
    """
    if not enabled:
        logger.info("Synthetic monitoring disabled")
        return

    # Enforce minimum interval (AC-001 edge case)
    initial_interval = max(interval_seconds, MINIMUM_INTERVAL_SECONDS)

    _state.enabled = True
    _state.interval_seconds = initial_interval

    logger.info(
        "Synthetic monitoring started",
        extra={"interval_seconds": initial_interval, "base_url": base_url},
    )

    while not shutdown_event.is_set():
        try:
            if engine is not None:
                from sqlmodel import Session as _Session

                with _Session(engine) as db_session:
                    result = await run_synthetic_check(
                        base_url=base_url,
                        api_key=api_key,
                        db_session=db_session,
                    )
                    # Store result in DB (AC-016)
                    try:
                        store_check_result(db_session, result)
                    except Exception:
                        logger.exception("Failed to store synthetic check result")
            else:
                await run_synthetic_check(
                    base_url=base_url,
                    api_key=api_key,
                )

        except Exception:
            logger.exception("Synthetic check cycle failed unexpectedly")

        # Read interval from state each cycle so UI changes take effect (SIG-1)
        effective_interval = max(_state.interval_seconds, MINIMUM_INTERVAL_SECONDS)

        # Wait for interval or shutdown
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=effective_interval)
            break  # Shutdown signaled
        except asyncio.TimeoutError:
            continue  # Interval elapsed, run again
