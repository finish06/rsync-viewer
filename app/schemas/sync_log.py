from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SyncLogCreate(BaseModel):
    source_name: str
    start_time: datetime
    end_time: datetime
    raw_content: str


class SyncLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_name: str
    start_time: datetime
    end_time: datetime
    total_size_bytes: Optional[int] = None
    bytes_sent: Optional[int] = None
    bytes_received: Optional[int] = None
    transfer_speed: Optional[float] = None
    file_count: Optional[int] = None
    status: str
    is_dry_run: bool = False
    created_at: datetime


class SyncLogList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_name: str
    start_time: datetime
    end_time: datetime
    total_size_bytes: Optional[int] = None
    bytes_received: Optional[int] = None
    transfer_speed: Optional[float] = None
    file_count: Optional[int] = None
    status: str
    is_dry_run: bool = False


class SyncLogDetail(SyncLogRead):
    raw_content: str
    file_list: Optional[list[str]] = None
    speedup_ratio: Optional[float] = None


class PaginatedResponse(BaseModel):
    items: list[SyncLogList]
    total: int
    offset: int
    limit: int


class SourceListResponse(BaseModel):
    sources: list[str]
