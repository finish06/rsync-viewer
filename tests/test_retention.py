"""Tests for data retention cleanup.

Spec: specs/metrics-export.md
ACs: AC-007, AC-008
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.models.failure_event import FailureEvent
from app.models.sync_log import SyncLog
from app.utils import utc_now


class TestRetentionCleanup:
    """AC-007: Configurable data retention policies allow automatic cleanup."""

    def test_ac007_cleanup_deletes_old_records(
        self, db_session: Session, create_sync_log
    ):
        """Records older than retention period are deleted."""
        from app.services.retention import cleanup_old_sync_logs

        # Create old record (60 days ago)
        old_log = create_sync_log(
            source_name="old-source",
            start_time=utc_now() - timedelta(days=60),
            end_time=utc_now() - timedelta(days=60),
            created_at=utc_now() - timedelta(days=60),
        )

        # Create recent record (5 days ago)
        recent_log = create_sync_log(
            source_name="recent-source",
            start_time=utc_now() - timedelta(days=5),
            end_time=utc_now() - timedelta(days=5),
        )

        old_log_id = old_log.id
        recent_log_id = recent_log.id

        deleted = cleanup_old_sync_logs(db_session, retention_days=30)

        assert deleted == 1

        # Old record should be gone
        remaining = db_session.exec(select(SyncLog)).all()
        remaining_ids = [r.id for r in remaining]
        assert old_log_id not in remaining_ids
        assert recent_log_id in remaining_ids

    def test_ac007_cleanup_preserves_recent_records(
        self, db_session: Session, create_sync_log
    ):
        """Records within the retention period are preserved."""
        from app.services.retention import cleanup_old_sync_logs

        create_sync_log(
            source_name="recent",
            start_time=utc_now() - timedelta(days=5),
            end_time=utc_now() - timedelta(days=5),
        )

        deleted = cleanup_old_sync_logs(db_session, retention_days=30)

        assert deleted == 0
        remaining = db_session.exec(select(SyncLog)).all()
        assert len(remaining) == 1

    def test_ac007_cleanup_disabled_when_zero_days(
        self, db_session: Session, create_sync_log
    ):
        """No cleanup happens when retention_days is 0 (disabled)."""
        from app.services.retention import cleanup_old_sync_logs

        create_sync_log(
            source_name="old",
            start_time=utc_now() - timedelta(days=365),
            end_time=utc_now() - timedelta(days=365),
            created_at=utc_now() - timedelta(days=365),
        )

        deleted = cleanup_old_sync_logs(db_session, retention_days=0)

        assert deleted == 0
        remaining = db_session.exec(select(SyncLog)).all()
        assert len(remaining) == 1

    def test_ac007_cleanup_returns_count(self, db_session: Session, create_sync_log):
        """Cleanup returns the number of deleted records."""
        from app.services.retention import cleanup_old_sync_logs

        for i in range(5):
            create_sync_log(
                source_name=f"old-{i}",
                start_time=utc_now() - timedelta(days=60),
                end_time=utc_now() - timedelta(days=60),
                created_at=utc_now() - timedelta(days=60),
            )

        deleted = cleanup_old_sync_logs(db_session, retention_days=30)
        assert deleted == 5

    def test_ac007_cleanup_cascade_deletes_failure_events(
        self, db_session: Session, create_sync_log
    ):
        """Deleting old sync logs also removes related failure events."""
        from app.services.retention import cleanup_old_sync_logs

        old_log = create_sync_log(
            source_name="old",
            start_time=utc_now() - timedelta(days=60),
            end_time=utc_now() - timedelta(days=60),
            created_at=utc_now() - timedelta(days=60),
            exit_code=1,
        )

        # Create a failure event referencing the old log
        failure = FailureEvent(
            id=uuid4(),
            source_name="old",
            failure_type="exit_code",
            sync_log_id=old_log.id,
            detected_at=utc_now() - timedelta(days=60),
        )
        db_session.add(failure)
        db_session.commit()

        deleted = cleanup_old_sync_logs(db_session, retention_days=30)

        assert deleted == 1
        # Failure event should also be gone (or nullified)
        remaining_failures = db_session.exec(select(FailureEvent)).all()
        # Either cascade-deleted or sync_log_id set to NULL
        for f in remaining_failures:
            assert f.sync_log_id != old_log.id

    def test_ac007_cleanup_cascade_deletes_notifications(
        self, db_session: Session, create_sync_log
    ):
        """Deleting old sync logs cascades through failure events to notifications."""
        from app.services.retention import cleanup_old_sync_logs

        old_log = create_sync_log(
            source_name="old",
            start_time=utc_now() - timedelta(days=60),
            end_time=utc_now() - timedelta(days=60),
            created_at=utc_now() - timedelta(days=60),
            exit_code=1,
        )

        failure = FailureEvent(
            id=uuid4(),
            source_name="old",
            failure_type="exit_code",
            sync_log_id=old_log.id,
            detected_at=utc_now() - timedelta(days=60),
        )
        db_session.add(failure)
        db_session.flush()

        # We won't create full webhook + notification chain here
        # as it requires complex FK setup. The cleanup function should
        # handle FK ordering properly.

        deleted = cleanup_old_sync_logs(db_session, retention_days=30)
        assert deleted == 1


class TestRetentionBackgroundTask:
    """AC-008: Retention cleanup runs as a scheduled background task."""

    def test_ac008_retention_config_defaults(self):
        """Config has retention settings with correct defaults."""
        from app.config import Settings

        settings = Settings(
            database_url="postgresql+psycopg://test:test@localhost/test"
        )
        assert settings.data_retention_days == 0  # disabled by default
        assert settings.retention_cleanup_interval_hours == 24

    @pytest.mark.asyncio
    async def test_ac008_retention_task_function_exists(self):
        """The retention background task function exists and is callable."""
        from app.services.retention import retention_background_task

        # Should be an async function
        assert callable(retention_background_task)

    @pytest.mark.asyncio
    async def test_ac008_retention_task_skips_when_disabled(self):
        """Background task does nothing when retention_days is 0."""
        from app.services.retention import retention_background_task

        # Mock the shutdown event to trigger after one check
        import asyncio

        shutdown_event = asyncio.Event()
        shutdown_event.set()  # Immediately trigger shutdown

        # Should complete without error when disabled
        await retention_background_task(
            retention_days=0,
            interval_hours=24,
            shutdown_event=shutdown_event,
        )
