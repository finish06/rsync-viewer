from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class SyncSourceMonitor(SQLModel, table=True):
    __tablename__ = "sync_source_monitors"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_name: str = Field(max_length=100, unique=True, index=True)
    expected_interval_hours: int
    grace_multiplier: float = Field(default=1.5)
    enabled: bool = Field(default=True)
    last_sync_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
