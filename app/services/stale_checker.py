import logging
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.models.failure_event import FailureEvent
from app.models.monitor import SyncSourceMonitor

logger = logging.getLogger(__name__)


def check_stale_sources(session: Session) -> list[FailureEvent]:
    """Check all enabled monitors for stale sync sources.

    A source is stale when:
        now - last_sync_at > expected_interval_hours * grace_multiplier

    Monitors without a last_sync_at (never synced) are skipped.
    Disabled monitors are skipped.
    Duplicate stale events are not created if one already exists
    since the last sync.

    Returns a list of newly created FailureEvent objects.
    """
    monitors = session.exec(
        select(SyncSourceMonitor).where(SyncSourceMonitor.enabled.is_(True))
    ).all()

    new_events: list[FailureEvent] = []
    now = datetime.utcnow()

    for monitor in monitors:
        # Skip monitors that have never synced
        if monitor.last_sync_at is None:
            continue

        # Calculate the deadline
        deadline_hours = monitor.expected_interval_hours * monitor.grace_multiplier
        deadline = monitor.last_sync_at + timedelta(hours=deadline_hours)

        if now <= deadline:
            continue  # Not stale yet

        # Check for existing stale event since last sync to avoid duplicates
        existing = session.exec(
            select(FailureEvent).where(
                FailureEvent.source_name == monitor.source_name,
                FailureEvent.failure_type == "stale",
                FailureEvent.detected_at >= monitor.last_sync_at,
            )
        ).first()

        if existing:
            continue  # Already flagged

        hours_overdue = (now - deadline).total_seconds() / 3600
        event = FailureEvent(
            source_name=monitor.source_name,
            failure_type="stale",
            details=(
                f"No sync for {monitor.source_name} in "
                f"{(now - monitor.last_sync_at).total_seconds() / 3600:.1f}h "
                f"(expected every {monitor.expected_interval_hours}h, "
                f"grace {monitor.grace_multiplier}x)"
            ),
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        new_events.append(event)

        logger.info(
            "Stale source detected",
            extra={
                "source_name": monitor.source_name,
                "hours_overdue": round(hours_overdue, 1),
            },
        )

    return new_events
