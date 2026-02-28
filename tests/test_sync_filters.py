"""Tests for app.services.sync_filters — apply_sync_filters() and InvalidDateError.

Covers all filter combinations: source_name, date range, dry_run, hide_empty,
plus edge cases like invalid dates and combined filters.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.sync_log import SyncLog
from app.services.sync_filters import InvalidDateError, apply_sync_filters


@event.listens_for(SQLModel.metadata, "column_reflect")
def _fix_jsonb(inspector, table, column_info):
    if isinstance(column_info.get("type"), JSONB):
        column_info["type"] = JSON()


@pytest.fixture(scope="module")
def sqlite_engine():
    """Create a SQLite in-memory engine with JSONB mapped to JSON."""
    engine = create_engine("sqlite://", echo=False)
    # Swap JSONB columns to JSON before creating tables
    for table in SQLModel.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(autouse=True)
def session(sqlite_engine):
    """Per-test session with rollback."""
    connection = sqlite_engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection)
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


def _make_log(
    session: Session,
    *,
    source_name: str = "backup",
    start_time: datetime | None = None,
    is_dry_run: bool = False,
    file_count: int | None = 5,
) -> SyncLog:
    """Helper to insert a SyncLog row."""
    now = datetime.now()
    log = SyncLog(
        id=uuid4(),
        source_name=source_name,
        start_time=start_time or now,
        end_time=now + timedelta(minutes=5),
        raw_content="test",
        is_dry_run=is_dry_run,
        file_count=file_count,
    )
    session.add(log)
    session.flush()
    return log


# ---------- InvalidDateError ----------


class TestInvalidDateError:
    def test_invalid_date_error_message(self):
        err = InvalidDateError("not-a-date")
        assert "not-a-date" in str(err)
        assert err.value == "not-a-date"

    def test_invalid_date_error_is_value_error(self):
        assert issubclass(InvalidDateError, ValueError)


# ---------- Source name filter ----------


class TestSourceNameFilter:
    def test_filter_by_source_name(self, session):
        _make_log(session, source_name="photos")
        _make_log(session, source_name="documents")

        stmt = apply_sync_filters(
            select(SyncLog),
            source_name="photos",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].source_name == "photos"

    def test_no_source_filter_returns_all(self, session):
        _make_log(session, source_name="alpha")
        _make_log(session, source_name="beta")

        stmt = apply_sync_filters(
            select(SyncLog),
            source_name=None,
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 2

    def test_empty_string_source_name_returns_all(self, session):
        _make_log(session, source_name="gamma")
        _make_log(session, source_name="delta")

        stmt = apply_sync_filters(
            select(SyncLog),
            source_name="",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 2


# ---------- Date range filters ----------


class TestDateRangeFilter:
    def test_filter_start_date(self, session):
        _make_log(session, start_time=datetime(2025, 1, 1, 12, 0))
        _make_log(session, start_time=datetime(2025, 6, 15, 12, 0))

        stmt = apply_sync_filters(
            select(SyncLog),
            start_date="2025-03-01",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].start_time.month == 6

    def test_filter_end_date(self, session):
        _make_log(session, start_time=datetime(2025, 1, 1, 12, 0))
        _make_log(session, start_time=datetime(2025, 6, 15, 12, 0))

        stmt = apply_sync_filters(
            select(SyncLog),
            end_date="2025-03-01",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].start_time.month == 1

    def test_filter_date_range_both(self, session):
        _make_log(session, start_time=datetime(2025, 1, 1))
        _make_log(session, start_time=datetime(2025, 3, 15))
        _make_log(session, start_time=datetime(2025, 6, 1))

        stmt = apply_sync_filters(
            select(SyncLog),
            start_date="2025-02-01",
            end_date="2025-04-01",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].start_time.month == 3

    def test_invalid_start_date_raises(self):
        with pytest.raises(InvalidDateError) as exc_info:
            apply_sync_filters(
                select(SyncLog),
                start_date="not-a-date",
                show_dry_run="show",
                hide_empty="show",
            )
        assert exc_info.value.value == "not-a-date"

    def test_invalid_end_date_raises(self):
        with pytest.raises(InvalidDateError):
            apply_sync_filters(
                select(SyncLog),
                end_date="13/99/2025",
                show_dry_run="show",
                hide_empty="show",
            )


# ---------- Dry-run filter ----------


class TestDryRunFilter:
    def test_hide_dry_run_default(self, session):
        _make_log(session, is_dry_run=False)
        _make_log(session, is_dry_run=True)

        stmt = apply_sync_filters(
            select(SyncLog),
            show_dry_run="hide",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].is_dry_run is False

    def test_only_dry_run(self, session):
        _make_log(session, is_dry_run=False)
        _make_log(session, is_dry_run=True)

        stmt = apply_sync_filters(
            select(SyncLog),
            show_dry_run="only",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].is_dry_run is True

    def test_show_all_dry_run(self, session):
        _make_log(session, is_dry_run=False)
        _make_log(session, is_dry_run=True)

        stmt = apply_sync_filters(
            select(SyncLog),
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 2


# ---------- Hide-empty filter ----------


class TestHideEmptyFilter:
    def test_hide_empty_default(self, session):
        _make_log(session, file_count=10)
        _make_log(session, file_count=0)

        stmt = apply_sync_filters(
            select(SyncLog),
            show_dry_run="show",
            hide_empty="hide",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].file_count == 10

    def test_only_empty(self, session):
        _make_log(session, file_count=10)
        _make_log(session, file_count=0)

        stmt = apply_sync_filters(
            select(SyncLog),
            show_dry_run="show",
            hide_empty="only",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].file_count == 0

    def test_show_all_empty(self, session):
        _make_log(session, file_count=10)
        _make_log(session, file_count=0)

        stmt = apply_sync_filters(
            select(SyncLog),
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 2

    def test_none_file_count_treated_as_empty(self, session):
        _make_log(session, file_count=None)
        _make_log(session, file_count=5)

        stmt = apply_sync_filters(
            select(SyncLog),
            show_dry_run="show",
            hide_empty="only",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].file_count is None


# ---------- Combined filters ----------


class TestCombinedFilters:
    def test_source_and_date_and_dry_run(self, session):
        # Match: source=photos, in range, not dry run
        _make_log(
            session,
            source_name="photos",
            start_time=datetime(2025, 3, 15),
            is_dry_run=False,
        )
        # No match: wrong source
        _make_log(
            session,
            source_name="docs",
            start_time=datetime(2025, 3, 15),
            is_dry_run=False,
        )
        # No match: dry run
        _make_log(
            session,
            source_name="photos",
            start_time=datetime(2025, 3, 15),
            is_dry_run=True,
        )
        # No match: outside date range
        _make_log(
            session,
            source_name="photos",
            start_time=datetime(2025, 1, 1),
            is_dry_run=False,
        )

        stmt = apply_sync_filters(
            select(SyncLog),
            source_name="photos",
            start_date="2025-02-01",
            end_date="2025-04-01",
            show_dry_run="hide",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].source_name == "photos"
        assert results[0].is_dry_run is False

    def test_all_defaults_hide_dry_and_empty(self, session):
        """Default parameters hide dry runs and empty runs."""
        _make_log(session, is_dry_run=False, file_count=5)
        _make_log(session, is_dry_run=True, file_count=5)
        _make_log(session, is_dry_run=False, file_count=0)

        stmt = apply_sync_filters(select(SyncLog))
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].is_dry_run is False
        assert results[0].file_count == 5

    def test_no_matching_source_returns_empty(self, session):
        _make_log(session, source_name="backup")

        stmt = apply_sync_filters(
            select(SyncLog),
            source_name="nonexistent",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 0
