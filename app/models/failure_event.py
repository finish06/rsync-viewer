from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class FailureEvent(SQLModel, table=True):
    __tablename__ = "failure_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_name: str = Field(max_length=100, index=True)
    failure_type: str = Field(max_length=20)  # "exit_code" or "stale"
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    sync_log_id: Optional[UUID] = Field(default=None, foreign_key="sync_logs.id")
    notified: bool = Field(default=False)
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
