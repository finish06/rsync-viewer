"""Per-source health rollup for the Overview cards (specs/insight-ui.md AC-005)."""

from datetime import date, datetime, timedelta
from typing import Optional

from sqlmodel import Session, case, col, func, select

from app.models.monitor import SyncSourceMonitor
from app.models.sync_log import SyncLog
from app.schemas.source_health import DailyPoint, SourceHealth
from app.services.synthetic_check import SYNTHETIC_SOURCE_NAME
from app.utils import utc_now


def _is_failure(exit_code: Optional[int]) -> bool:
    return exit_code is not None and exit_code != 0


def _window_start(now: datetime, days: int) -> datetime:
    start_day = now.date() - timedelta(days=days - 1)
    return datetime.combine(start_day, datetime.min.time(), tzinfo=now.tzinfo)


def _daily_series(
    session: Session, window_start: datetime
) -> dict[str, dict[date, DailyPoint]]:
    """One grouped query: per source and UTC day → syncs, failures, bytes."""
    day = func.date(SyncLog.start_time).label("day")
    failures = func.sum(case((col(SyncLog.exit_code) != 0, 1), else_=0))
    stmt = (
        select(  # type: ignore[call-overload]  # sqlmodel overloads stop at 4 columns
            SyncLog.source_name,
            day,
            func.count().label("syncs"),
            failures.label("failures"),
            func.coalesce(func.sum(SyncLog.bytes_received), 0).label("bytes"),
        )
        .where(
            col(SyncLog.is_dry_run).is_(False),
            col(SyncLog.source_name) != SYNTHETIC_SOURCE_NAME,
            col(SyncLog.start_time) >= window_start,
        )
        .group_by(SyncLog.source_name, day)
    )
    series: dict[str, dict[date, DailyPoint]] = {}
    for source_name, day_value, syncs, fails, total_bytes in session.exec(stmt).all():
        series.setdefault(source_name, {})[day_value] = DailyPoint(
            date=day_value,
            syncs=int(syncs),
            failures=int(fails or 0),
            bytes=int(total_bytes or 0),
        )
    return series


def _latest_per_source(session: Session) -> dict[str, SyncLog]:
    """Most recent real sync per source (PostgreSQL DISTINCT ON)."""
    stmt = (
        select(SyncLog)
        .where(
            col(SyncLog.is_dry_run).is_(False),
            col(SyncLog.source_name) != SYNTHETIC_SOURCE_NAME,
        )
        .distinct(col(SyncLog.source_name))
        .order_by(col(SyncLog.source_name), col(SyncLog.start_time).desc())
    )
    return {row.source_name: row for row in session.exec(stmt).all()}


def _consecutive_failures(
    session: Session, window_start: datetime, latest: dict[str, SyncLog]
) -> dict[str, int]:
    """Length of the current failure streak per source, bounded by the window."""
    stmt = (
        select(SyncLog.source_name, SyncLog.exit_code)
        .where(
            col(SyncLog.is_dry_run).is_(False),
            col(SyncLog.source_name) != SYNTHETIC_SOURCE_NAME,
            col(SyncLog.start_time) >= window_start,
        )
        .order_by(col(SyncLog.start_time).desc())
    )
    streaks: dict[str, int] = {}
    closed: set[str] = set()
    for source_name, exit_code in session.exec(stmt).all():
        if source_name in closed:
            continue
        if _is_failure(exit_code):
            streaks[source_name] = streaks.get(source_name, 0) + 1
        else:
            closed.add(source_name)
    # Sources whose latest sync is older than the window still count that one
    for source_name, log in latest.items():
        if source_name not in streaks and source_name not in closed:
            streaks[source_name] = 1 if _is_failure(log.exit_code) else 0
    return streaks


def _stale(monitor: Optional[SyncSourceMonitor], last_sync_at, now: datetime) -> bool:
    if monitor is None or not monitor.enabled:
        return False
    reference = monitor.last_sync_at or last_sync_at
    if reference is None:
        return False
    deadline_hours = monitor.expected_interval_hours * monitor.grace_multiplier
    return now > reference + timedelta(hours=deadline_hours)


def get_source_health(session: Session, days: int = 14) -> list[SourceHealth]:
    """Build the health card payload for every source (logs or monitors)."""
    now = utc_now()
    window_start = _window_start(now, days)
    series = _daily_series(session, window_start)
    latest = _latest_per_source(session)
    streaks = _consecutive_failures(session, window_start, latest)
    monitors = {m.source_name: m for m in session.exec(select(SyncSourceMonitor)).all()}

    day_axis = [window_start.date() + timedelta(days=i) for i in range(days)]
    result: list[SourceHealth] = []
    for source_name in sorted(set(latest) | set(monitors)):
        log = latest.get(source_name)
        monitor = monitors.get(source_name)
        per_day = series.get(source_name, {})
        last_sync_at = log.end_time if log else None
        if log is None:
            last_status = "never"
        elif _is_failure(log.exit_code):
            last_status = "failed"
        else:
            last_status = "ok"
        result.append(
            SourceHealth(
                source_name=source_name,
                last_sync_at=last_sync_at,
                last_status=last_status,
                last_exit_code=log.exit_code if log else None,
                consecutive_failures=streaks.get(source_name, 0),
                expected_interval_hours=(
                    monitor.expected_interval_hours if monitor else None
                ),
                is_stale=_stale(monitor, last_sync_at, now),
                daily=[per_day.get(d, DailyPoint(date=d)) for d in day_axis],
            )
        )
    return result
