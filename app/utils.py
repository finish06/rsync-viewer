"""Shared utility functions."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC time as a naive datetime.

    Uses the non-deprecated datetime.now(UTC) internally, then strips
    tzinfo so the result is compatible with PostgreSQL
    ``timestamp without time zone`` columns (which return naive datetimes).
    """
    return datetime.now(UTC).replace(tzinfo=None)
