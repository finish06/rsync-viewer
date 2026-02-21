from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SyncLogCreate(BaseModel):
    """Schema for creating a new sync log entry"""

    source_name: str = Field(
        ...,
        description="Identifier for the sync source (e.g., 'backup-server', 'media-sync')",
        examples=["backup-server"],
    )
    start_time: datetime = Field(
        ...,
        description="When the rsync operation started",
        examples=["2024-01-15T10:00:00Z"],
    )
    end_time: datetime = Field(
        ...,
        description="When the rsync operation completed",
        examples=["2024-01-15T10:05:30Z"],
    )
    raw_content: str = Field(
        ...,
        description="Raw rsync command output to be parsed",
        examples=[
            "sending incremental file list\nfile1.txt\nsent 1.23K bytes received 45 bytes 850.00 bytes/sec\ntotal size is 5.67M speedup is 4,444.88"
        ],
    )
    exit_code: Optional[int] = Field(
        default=None,
        description="Rsync process exit code (0=success, non-zero=failure)",
        examples=[0],
    )


class SyncLogRead(BaseModel):
    """Schema for sync log response (summary view)"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique identifier for the sync log")
    source_name: str = Field(..., description="Identifier for the sync source")
    start_time: datetime = Field(..., description="When the rsync operation started")
    end_time: datetime = Field(..., description="When the rsync operation completed")
    total_size_bytes: Optional[int] = Field(
        None, description="Total size of files in bytes"
    )
    bytes_sent: Optional[int] = Field(None, description="Bytes sent during transfer")
    bytes_received: Optional[int] = Field(
        None, description="Bytes received during transfer"
    )
    transfer_speed: Optional[float] = Field(
        None, description="Transfer speed in bytes/sec"
    )
    file_count: Optional[int] = Field(None, description="Number of files transferred")
    exit_code: Optional[int] = Field(
        None, description="Rsync process exit code"
    )
    status: str = Field(..., description="Sync status (completed, failed, etc.)")
    is_dry_run: bool = Field(
        False, description="Whether this was a dry run (no actual transfer)"
    )
    created_at: datetime = Field(..., description="When this log entry was created")


class SyncLogList(BaseModel):
    """Schema for sync log in list view (reduced fields)"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique identifier for the sync log")
    source_name: str = Field(..., description="Identifier for the sync source")
    start_time: datetime = Field(..., description="When the rsync operation started")
    end_time: datetime = Field(..., description="When the rsync operation completed")
    total_size_bytes: Optional[int] = Field(
        None, description="Total size of files in bytes"
    )
    bytes_received: Optional[int] = Field(
        None, description="Bytes received during transfer"
    )
    transfer_speed: Optional[float] = Field(
        None, description="Transfer speed in bytes/sec"
    )
    file_count: Optional[int] = Field(None, description="Number of files transferred")
    status: str = Field(..., description="Sync status (completed, failed, etc.)")
    is_dry_run: bool = Field(False, description="Whether this was a dry run")


class SyncLogDetail(SyncLogRead):
    """Schema for detailed sync log view (includes raw content and file list)"""

    raw_content: str = Field(..., description="Original rsync command output")
    file_list: Optional[list[str]] = Field(
        None, description="List of files that were transferred"
    )
    speedup_ratio: Optional[float] = Field(None, description="Rsync speedup ratio")


class PaginatedResponse(BaseModel):
    """Paginated list of sync logs"""

    items: list[SyncLogList] = Field(..., description="List of sync log entries")
    total: int = Field(
        ..., description="Total number of matching records", examples=[42]
    )
    offset: int = Field(..., description="Current pagination offset", examples=[0])
    limit: int = Field(..., description="Page size limit", examples=[50])


class SourceListResponse(BaseModel):
    """List of unique sync source names"""

    sources: list[str] = Field(
        ...,
        description="List of unique source names",
        examples=[["backup-server", "media-sync", "documents"]],
    )


class ErrorResponse(BaseModel):
    """Standard error response"""

    detail: str = Field(
        ..., description="Error message", examples=["Sync log not found"]
    )
