"""Synthetic monitoring service.

Periodically POSTs a canned rsync log to the app's own API, verifies the
response, DELETEs it on success, and fires webhooks on failure.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
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


def get_state() -> SyntheticCheckState:
    """Return current synthetic check state."""
    return _state


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

    Mirrors the retention_background_task pattern from app/services/retention.py.

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
                    await run_synthetic_check(
                        base_url=base_url,
                        api_key=api_key,
                        db_session=db_session,
                    )
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
