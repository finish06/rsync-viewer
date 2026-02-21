"""Tests for stale sync detection service.

Covers: AC-003, AC-004, AC-009, AC-010
"""

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session

from app.models.monitor import SyncSourceMonitor
from app.services.stale_checker import check_stale_sources


@pytest.fixture
def create_monitor(db_session: Session):
    """Factory fixture to create monitors in the database."""
    from uuid import uuid4

    def _create(
        source_name: str = "test-source",
        expected_interval_hours: int = 24,
        grace_multiplier: float = 1.5,
        enabled: bool = True,
        last_sync_at: datetime = None,
    ) -> SyncSourceMonitor:
        monitor = SyncSourceMonitor(
            id=uuid4(),
            source_name=source_name,
            expected_interval_hours=expected_interval_hours,
            grace_multiplier=grace_multiplier,
            enabled=enabled,
            last_sync_at=last_sync_at,
        )
        db_session.add(monitor)
        db_session.commit()
        db_session.refresh(monitor)
        return monitor

    return _create


# --- AC-003: Background scheduler checks for stale sources ---


def test_ac003_stale_source_detected(db_session, create_monitor):
    """Source that hasn't synced within interval * grace should be flagged stale."""
    # Last sync was 37 hours ago, interval is 24h, grace 1.5 → deadline 36h
    create_monitor(
        source_name="stale-server",
        expected_interval_hours=24,
        grace_multiplier=1.5,
        last_sync_at=datetime.utcnow() - timedelta(hours=37),
    )

    events = check_stale_sources(db_session)

    assert len(events) == 1
    assert events[0].failure_type == "stale"
    assert events[0].source_name == "stale-server"


def test_ac003_source_within_grace_not_flagged(db_session, create_monitor):
    """Source within grace period should NOT be flagged."""
    # Last sync was 30 hours ago, interval 24h, grace 1.5 → deadline 36h
    create_monitor(
        source_name="ok-server",
        expected_interval_hours=24,
        grace_multiplier=1.5,
        last_sync_at=datetime.utcnow() - timedelta(hours=30),
    )

    events = check_stale_sources(db_session)
    assert len(events) == 0


def test_ac003_recently_synced_not_flagged(db_session, create_monitor):
    """Source that synced recently should NOT be flagged."""
    create_monitor(
        source_name="recent-server",
        expected_interval_hours=24,
        last_sync_at=datetime.utcnow() - timedelta(hours=1),
    )

    events = check_stale_sources(db_session)
    assert len(events) == 0


# --- AC-004: Stale sources generate FailureEvent ---


def test_ac004_stale_creates_failure_event(db_session, create_monitor):
    """Stale detection should create a FailureEvent with type 'stale'."""
    create_monitor(
        source_name="stale-source",
        expected_interval_hours=24,
        last_sync_at=datetime.utcnow() - timedelta(hours=37),
    )

    events = check_stale_sources(db_session)

    assert len(events) == 1
    event = events[0]
    assert event.failure_type == "stale"
    assert event.sync_log_id is None  # No specific sync log for stale failures
    assert event.notified is False
    assert event.details is not None


def test_ac004_no_duplicate_stale_events(db_session, create_monitor):
    """Running stale check twice should NOT create duplicate events."""
    create_monitor(
        source_name="stale-once",
        expected_interval_hours=24,
        last_sync_at=datetime.utcnow() - timedelta(hours=37),
    )

    events1 = check_stale_sources(db_session)
    assert len(events1) == 1

    events2 = check_stale_sources(db_session)
    assert len(events2) == 0  # No new events


# --- AC-009: Sources without frequency not checked ---


def test_ac009_disabled_monitor_not_checked(db_session, create_monitor):
    """Monitors with enabled=False should not be checked."""
    create_monitor(
        source_name="disabled-server",
        expected_interval_hours=24,
        enabled=False,
        last_sync_at=datetime.utcnow() - timedelta(hours=100),
    )

    events = check_stale_sources(db_session)
    assert len(events) == 0


def test_ac009_no_last_sync_not_checked(db_session, create_monitor):
    """Monitor with no last_sync_at (never synced) should not be flagged."""
    create_monitor(
        source_name="never-synced",
        expected_interval_hours=24,
        last_sync_at=None,
    )

    events = check_stale_sources(db_session)
    assert len(events) == 0


# --- AC-010: Configurable grace multiplier in stale check ---


def test_ac010_custom_grace_multiplier_in_check(db_session, create_monitor):
    """Stale check should respect per-source grace multiplier."""
    # 25 hours ago, interval 24h, grace 2.0 → deadline 48h → NOT stale
    create_monitor(
        source_name="generous-grace",
        expected_interval_hours=24,
        grace_multiplier=2.0,
        last_sync_at=datetime.utcnow() - timedelta(hours=25),
    )

    events = check_stale_sources(db_session)
    assert len(events) == 0


def test_ac010_tight_grace_multiplier_flags_sooner(db_session, create_monitor):
    """Tighter grace multiplier should flag sooner."""
    # 14 hours ago, interval 12h, grace 1.1 → deadline 13.2h → stale!
    create_monitor(
        source_name="tight-grace",
        expected_interval_hours=12,
        grace_multiplier=1.1,
        last_sync_at=datetime.utcnow() - timedelta(hours=14),
    )

    events = check_stale_sources(db_session)
    assert len(events) == 1
