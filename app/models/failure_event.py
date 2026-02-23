from datetime import datetime
from app.utils import utc_now
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class FailureEvent(SQLModel, table=True):
    __tablename__ = "failure_events"
    __table_args__ = (
        Index(
            "ix_failure_events_source_name_detected_at", "source_name", "detected_at"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_name: str = Field(max_length=100, index=True)
    failure_type: str = Field(max_length=20, index=True)  # "exit_code" or "stale"
    detected_at: datetime = Field(default_factory=utc_now, index=True)
    sync_log_id: Optional[UUID] = Field(default=None, foreign_key="sync_logs.id")
    notified: bool = Field(default=False)
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
