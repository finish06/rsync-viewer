"""Response schemas for the synthetic monitoring API (specs/insight-ui.md)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SyntheticStatus(BaseModel):
    """Current liveness summary used by the SPA header pill (AC-002)."""

    enabled: bool
    status: str = Field(description="passing | failing | unknown | disabled")
    last_check_at: Optional[datetime] = None
    last_latency_ms: Optional[float] = None
    interval_seconds: int
    uptime_24h_pct: Optional[float] = None
    uptime_7d_pct: Optional[float] = None
    checks_24h: int = 0


class SyntheticCheckRead(BaseModel):
    """One stored synthetic check result (AC-003)."""

    checked_at: datetime
    status: str
    latency_ms: float
    error: Optional[str] = None
