from datetime import datetime
from app.utils import utc_now
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import BigInteger, Index
from sqlalchemy.dialects.postgresql import JSONB


class SyncLogBase(SQLModel):
    source_name: str = Field(max_length=100, index=True)
    start_time: datetime = Field(index=True)
    end_time: datetime
    raw_content: str


class SyncLog(SyncLogBase, table=True):
    __tablename__ = "sync_logs"
    __table_args__ = (
        Index("ix_sync_logs_source_name_created_at", "source_name", "created_at"),
        Index("ix_sync_logs_exit_code", "exit_code"),
        Index("ix_sync_logs_created_at", "created_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    total_size_bytes: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    bytes_sent: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    bytes_received: Optional[int] = Field(default=None, sa_column=Column(BigInteger))
    transfer_speed: Optional[float] = None
    speedup_ratio: Optional[float] = None
    file_count: Optional[int] = None
    file_list: Optional[list[str]] = Field(default=None, sa_column=Column(JSONB))
    exit_code: Optional[int] = None
    status: str = Field(default="completed", max_length=20)
    is_dry_run: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    key_hash: str = Field(max_length=128, unique=True)
    key_prefix: str = Field(default="", max_length=12)
    name: str = Field(max_length=100)
    source_names: Optional[list[str]] = Field(default=None, sa_column=Column(JSONB))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
