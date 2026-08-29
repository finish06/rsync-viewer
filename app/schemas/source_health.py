"""Response schemas for per-source health (specs/insight-ui.md AC-005)."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class DailyPoint(BaseModel):
    """One day of activity for a source's sparkline."""

    date: date
    syncs: int = 0
    failures: int = 0
    bytes: int = 0


class SourceHealth(BaseModel):
    """At-a-glance health for one sync source."""

    source_name: str
    last_sync_at: Optional[datetime] = None
    last_status: str = Field(description="ok | failed | never")
    last_exit_code: Optional[int] = None
    consecutive_failures: int = 0
    expected_interval_hours: Optional[int] = None
    is_stale: bool = False
    daily: list[DailyPoint]
