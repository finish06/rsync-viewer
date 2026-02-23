"""Analytics response schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SummaryPeriod(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class SummaryDataPoint(BaseModel):
    """A single aggregation bucket (day/week/month)."""

    date: str = Field(..., description="Period start date (ISO 8601)")
    total_syncs: int = Field(..., description="Total sync operations in period")
    successful_syncs: int = Field(..., description="Syncs with exit_code 0")
    failed_syncs: int = Field(..., description="Syncs with non-zero exit_code")
    avg_duration_seconds: Optional[float] = Field(
        None, description="Average sync duration in seconds"
    )
    total_bytes_transferred: Optional[int] = Field(
        None, description="Sum of bytes_received in period"
    )
    total_files_transferred: Optional[int] = Field(
        None, description="Sum of file_count in period"
    )


class SummaryResponse(BaseModel):
    """Response for GET /api/v1/analytics/summary."""

    period: str = Field(..., description="Aggregation period")
    start: str = Field(..., description="Query start date")
    end: str = Field(..., description="Query end date")
    data: list[SummaryDataPoint] = Field(
        default_factory=list, description="Aggregated data points"
    )


class SourceStats(BaseModel):
    """Per-source aggregate statistics."""

    source_name: str = Field(..., description="Sync source identifier")
    total_syncs: int = Field(..., description="Total sync operations")
    success_rate: float = Field(..., description="Fraction of syncs with exit_code 0")
    avg_duration_seconds: Optional[float] = Field(
        None, description="Average sync duration in seconds"
    )
    avg_files_transferred: Optional[float] = Field(
        None, description="Average file count per sync"
    )
    avg_bytes_transferred: Optional[float] = Field(
        None, description="Average bytes received per sync"
    )
    last_sync_at: Optional[datetime] = Field(
        None, description="Timestamp of most recent sync"
    )


class ExportRecord(BaseModel):
    """A single sync record for export."""

    source_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: Optional[float] = None
    file_count: Optional[int] = None
    bytes_received: Optional[int] = None
    bytes_sent: Optional[int] = None
    total_size_bytes: Optional[int] = None
    exit_code: Optional[int] = None
    status: Optional[str] = None
    is_dry_run: bool = False
