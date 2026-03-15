"""Data retention cleanup service.

Handles automatic cleanup of old sync logs based on configurable retention period.
"""

import asyncio
import logging
from datetime import timedelta

from sqlmodel import Session, func, select, delete

from app.models.failure_event import FailureEvent
from app.models.notification_log import NotificationLog
from app.models.sync_log import SyncLog
from app.utils import utc_now

logger = logging.getLogger(__name__)


def cleanup_old_sync_logs(session: Session, retention_days: int) -> int:
    """Delete sync logs older than the retention period.

    Handles FK cascade by deleting related records first:
    1. NotificationLogs referencing FailureEvents for old sync logs
    2. FailureEvents referencing old sync logs
    3. Old sync logs themselves

    Args:
        session: Database session.
        retention_days: Number of days to retain. 0 = disabled (no deletion).

    Returns:
        Number of sync logs deleted.
    """
    if retention_days <= 0:
        return 0

    cutoff = utc_now() - timedelta(days=retention_days)

    # Count before deleting (for logging)
    count = session.exec(
        select(func.count()).select_from(SyncLog).where(SyncLog.created_at < cutoff)
    ).one()

    if not count:
        return 0

    # Use correlated subqueries to avoid materializing large ID lists in Python
    old_sync_subq = select(SyncLog.id).where(SyncLog.created_at < cutoff).subquery()
    old_failure_subq = (
        select(FailureEvent.id)
        .where(FailureEvent.sync_log_id.in_(select(old_sync_subq.c.id)))  # type: ignore[union-attr]
        .subquery()
    )

    # Step 1: Delete notification logs via correlated subquery
    session.exec(
        delete(NotificationLog).where(
            NotificationLog.failure_event_id.in_(select(old_failure_subq.c.id))  # type: ignore[union-attr,attr-defined]
        )
    )

    # Step 2: Delete failure events via correlated subquery
    session.exec(
        delete(FailureEvent).where(
            FailureEvent.sync_log_id.in_(select(old_sync_subq.c.id))  # type: ignore[union-attr]
        )
    )

    # Step 3: Delete old sync logs
    session.exec(
        delete(SyncLog).where(SyncLog.created_at < cutoff)  # type: ignore[arg-type]
    )

    session.commit()

    logger.info(
        "Retention cleanup completed",
        extra={"deleted_count": count, "retention_days": retention_days},
    )

    return count


async def retention_background_task(
    retention_days: int,
    interval_hours: int,
    shutdown_event: asyncio.Event,
    engine=None,
) -> None:
    """Background task that periodically runs retention cleanup.

    Args:
        retention_days: Days to retain sync logs. 0 = disabled.
        interval_hours: Hours between cleanup runs.
        shutdown_event: Event signaling app shutdown.
        engine: SQLAlchemy engine for creating sessions.
    """
    if retention_days <= 0:
        logger.info("Data retention disabled (retention_days=0)")
        return

    logger.info(
        "Retention background task started",
        extra={
            "retention_days": retention_days,
            "interval_hours": interval_hours,
        },
    )

    interval_seconds = interval_hours * 3600

    while not shutdown_event.is_set():
        try:
            if engine is not None:
                with Session(engine) as session:
                    deleted = cleanup_old_sync_logs(session, retention_days)
                    if deleted > 0:
                        logger.info(
                            "Retention cleanup deleted records",
                            extra={"deleted_count": deleted},
                        )
        except Exception:
            logger.exception("Retention cleanup failed")

        # Wait for interval or shutdown
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=interval_seconds)
            break  # Shutdown signaled
        except asyncio.TimeoutError:
            continue  # Interval elapsed, run again
