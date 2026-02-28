"""Shared sync log query filters.

Eliminates duplication between htmx_sync_table() and htmx_charts() which
apply identical source / date-range / dry-run / hide-empty predicates.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import select

from app.models.sync_log import SyncLog


class InvalidDateError(ValueError):
    """Raised when a date string cannot be parsed."""

    def __init__(self, value: str):
        super().__init__(f"Invalid date format: {value}")
        self.value = value


def _parse_date(date_str: str) -> datetime:
    """Parse an ISO-format date string (e.g. ``2025-01-31``).

    Raises :class:`InvalidDateError` on unparseable input.
    """
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        raise InvalidDateError(date_str)


def apply_sync_filters(
    statement: select,  # type: ignore[type-arg]
    *,
    source_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    show_dry_run: str = "hide",
    hide_empty: str = "hide",
) -> select:  # type: ignore[type-arg]
    """Apply standard sync log filters to a SQLModel select statement.

    Parameters
    ----------
    statement : select
        A ``select(SyncLog)`` statement to filter.
    source_name : str, optional
        Filter to a specific source name.
    start_date : str, optional
        ISO date string (YYYY-MM-DD) — inclusive lower bound on start_time.
    end_date : str, optional
        ISO date string (YYYY-MM-DD) — inclusive upper bound on start_time.
    show_dry_run : str
        ``"hide"`` (exclude dry runs), ``"only"`` (only dry runs),
        or ``"show"`` (no filter).
    hide_empty : str
        ``"hide"`` (exclude zero-file runs), ``"only"`` (only zero-file runs),
        or ``"show"`` (no filter).

    Returns
    -------
    select
        The filtered statement.
    """
    if source_name:
        statement = statement.where(SyncLog.source_name == source_name)
    if start_date:
        statement = statement.where(SyncLog.start_time >= _parse_date(start_date))
    if end_date:
        statement = statement.where(SyncLog.start_time <= _parse_date(end_date))

    # Dry-run filter
    if show_dry_run == "hide":
        statement = statement.where(SyncLog.is_dry_run.is_(False))  # type: ignore[attr-defined]
    elif show_dry_run == "only":
        statement = statement.where(SyncLog.is_dry_run.is_(True))  # type: ignore[attr-defined]

    # Empty-run filter
    if hide_empty == "hide":
        statement = statement.where(SyncLog.file_count > 0)  # type: ignore[operator]
    elif hide_empty == "only":
        statement = statement.where(
            (SyncLog.file_count == 0) | (SyncLog.file_count == None)  # noqa: E711
        )

    return statement
