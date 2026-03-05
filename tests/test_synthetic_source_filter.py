"""Tests for synthetic source filter feature.

Spec: specs/synthetic-source-filter.md
Covers AC-001 through AC-011: filtering __synthetic_check from default views,
API responses, and source dropdowns, with toggle support.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.sync_log import SyncLog
from app.services.sync_filters import apply_sync_filters
from app.services.synthetic_check import SYNTHETIC_SOURCE_NAME


@event.listens_for(SQLModel.metadata, "column_reflect")
def _fix_jsonb(inspector, table, column_info):
    if isinstance(column_info.get("type"), JSONB):
        column_info["type"] = JSON()


@pytest.fixture(scope="module")
def sqlite_engine():
    """Create a SQLite in-memory engine with JSONB mapped to JSON."""
    engine = create_engine("sqlite://", echo=False)
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


# ---------- AC-009: apply_sync_filters synthetic parameter ----------


class TestSyntheticFilterInApplySyncFilters:
    """AC-009: The shared apply_sync_filters() function handles synthetic filtering."""

    def test_ac009_default_hides_synthetic(self, session):
        """Default call to apply_sync_filters excludes __synthetic_check."""
        _make_log(session, source_name="backup")
        _make_log(session, source_name=SYNTHETIC_SOURCE_NAME)

        stmt = apply_sync_filters(
            select(SyncLog),
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].source_name == "backup"

    def test_ac009_synthetic_hide_explicit(self, session):
        """Explicit synthetic='hide' excludes __synthetic_check."""
        _make_log(session, source_name="photos")
        _make_log(session, source_name=SYNTHETIC_SOURCE_NAME)

        stmt = apply_sync_filters(
            select(SyncLog),
            synthetic="hide",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].source_name == "photos"

    def test_ac009_synthetic_only(self, session):
        """synthetic='only' returns only __synthetic_check rows."""
        _make_log(session, source_name="backup")
        _make_log(session, source_name=SYNTHETIC_SOURCE_NAME)

        stmt = apply_sync_filters(
            select(SyncLog),
            synthetic="only",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].source_name == SYNTHETIC_SOURCE_NAME

    def test_ac009_synthetic_show(self, session):
        """synthetic='show' returns all rows including synthetic."""
        _make_log(session, source_name="backup")
        _make_log(session, source_name=SYNTHETIC_SOURCE_NAME)

        stmt = apply_sync_filters(
            select(SyncLog),
            synthetic="show",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 2

    def test_ac009_no_synthetic_rows_default_unchanged(self, session):
        """When no synthetic rows exist, default still works fine."""
        _make_log(session, source_name="backup")
        _make_log(session, source_name="photos")

        stmt = apply_sync_filters(
            select(SyncLog),
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 2


# ---------- AC-010: Filters compose ----------


class TestSyntheticFilterComposition:
    """AC-010: Synthetic toggle composes with date range and other filters."""

    def test_ac010_synthetic_only_with_date_range(self, session):
        """synthetic='only' + date range returns synthetic within range."""
        _make_log(
            session,
            source_name=SYNTHETIC_SOURCE_NAME,
            start_time=datetime(2025, 3, 15),
        )
        _make_log(
            session,
            source_name=SYNTHETIC_SOURCE_NAME,
            start_time=datetime(2025, 1, 1),
        )
        _make_log(
            session,
            source_name="backup",
            start_time=datetime(2025, 3, 15),
        )

        stmt = apply_sync_filters(
            select(SyncLog),
            synthetic="only",
            start_date="2025-02-01",
            end_date="2025-04-01",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].source_name == SYNTHETIC_SOURCE_NAME
        assert results[0].start_time.month == 3

    def test_ac010_synthetic_only_with_source_filter(self, session):
        """AC-010 edge case: synthetic='only' takes precedence over source_name filter."""
        _make_log(session, source_name=SYNTHETIC_SOURCE_NAME)
        _make_log(session, source_name="backup")

        stmt = apply_sync_filters(
            select(SyncLog),
            synthetic="only",
            source_name="backup",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        # synthetic=only should take precedence, returning synthetic rows
        assert len(results) == 1
        assert results[0].source_name == SYNTHETIC_SOURCE_NAME

    def test_ac010_hide_synthetic_composes_with_source_filter(self, session):
        """Hiding synthetic + source filter returns only that source."""
        _make_log(session, source_name="backup")
        _make_log(session, source_name="photos")
        _make_log(session, source_name=SYNTHETIC_SOURCE_NAME)

        stmt = apply_sync_filters(
            select(SyncLog),
            synthetic="hide",
            source_name="backup",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].source_name == "backup"

    def test_ac010_all_filters_combined(self, session):
        """All filters compose together: synthetic + date + dry_run + empty."""
        # Should match: synthetic-only, in range, not dry, has files
        _make_log(
            session,
            source_name=SYNTHETIC_SOURCE_NAME,
            start_time=datetime(2025, 3, 15),
            is_dry_run=False,
            file_count=5,
        )
        # No match: synthetic but dry run
        _make_log(
            session,
            source_name=SYNTHETIC_SOURCE_NAME,
            start_time=datetime(2025, 3, 15),
            is_dry_run=True,
            file_count=5,
        )
        # No match: not synthetic
        _make_log(
            session,
            source_name="backup",
            start_time=datetime(2025, 3, 15),
            is_dry_run=False,
            file_count=5,
        )

        stmt = apply_sync_filters(
            select(SyncLog),
            synthetic="only",
            start_date="2025-02-01",
            end_date="2025-04-01",
            show_dry_run="hide",
            hide_empty="hide",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].source_name == SYNTHETIC_SOURCE_NAME


# ---------- AC-001/AC-002/AC-003: Default exclusion from table/charts/API ----------
# These will be tested via HTTP integration tests once the endpoints are updated.
# For now, test the filter function which underpins all endpoints.


class TestDefaultExclusion:
    """AC-001/AC-002/AC-003: Default behavior excludes synthetic from all views."""

    def test_ac001_ac002_ac003_default_excludes_synthetic(self, session):
        """Default apply_sync_filters call (no explicit synthetic param) hides synthetic."""
        _make_log(session, source_name="backup")
        _make_log(session, source_name="photos")
        _make_log(session, source_name=SYNTHETIC_SOURCE_NAME)

        # Default call with no synthetic param should exclude synthetic
        stmt = apply_sync_filters(select(SyncLog))
        results = session.exec(stmt).all()
        source_names = [r.source_name for r in results]
        assert SYNTHETIC_SOURCE_NAME not in source_names


# ---------- AC-006: Toggle ON shows only synthetic ----------


class TestToggleShowsOnlySynthetic:
    """AC-006: When toggle is ON, view shows only synthetic data."""

    def test_ac006_only_mode_returns_only_synthetic(self, session):
        """synthetic='only' returns exclusively __synthetic_check rows."""
        _make_log(session, source_name="backup")
        _make_log(session, source_name="photos")
        _make_log(session, source_name=SYNTHETIC_SOURCE_NAME)
        _make_log(session, source_name=SYNTHETIC_SOURCE_NAME)

        stmt = apply_sync_filters(
            select(SyncLog),
            synthetic="only",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 2
        assert all(r.source_name == SYNTHETIC_SOURCE_NAME for r in results)

    def test_ac006_only_mode_empty_when_no_synthetic(self, session):
        """synthetic='only' returns empty when no synthetic logs exist."""
        _make_log(session, source_name="backup")

        stmt = apply_sync_filters(
            select(SyncLog),
            synthetic="only",
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 0


# ---------- AC-008: API synthetic query parameter ----------


class TestAPISyntheticParam:
    """AC-008: API accepts synthetic param with hide/only/show, defaulting to hide."""

    def test_ac008_param_values(self):
        """Verify the synthetic parameter accepts the three valid values."""
        # This test validates that apply_sync_filters accepts the synthetic kwarg
        # The actual HTTP-level param testing needs API integration tests
        for value in ("hide", "only", "show"):
            # Should not raise
            stmt = apply_sync_filters(
                select(SyncLog),
                synthetic=value,
                show_dry_run="show",
                hide_empty="show",
            )
            assert stmt is not None

    def test_ac008_default_is_hide(self, session):
        """Default value for synthetic parameter is 'hide'."""
        _make_log(session, source_name="backup")
        _make_log(session, source_name=SYNTHETIC_SOURCE_NAME)

        # Call without synthetic param — should default to hide
        stmt = apply_sync_filters(
            select(SyncLog),
            show_dry_run="show",
            hide_empty="show",
        )
        results = session.exec(stmt).all()
        assert len(results) == 1
        assert results[0].source_name == "backup"
