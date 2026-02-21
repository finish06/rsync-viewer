from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class NotificationLog(SQLModel, table=True):
    __tablename__ = "notification_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    failure_event_id: UUID = Field(foreign_key="failure_events.id", index=True)
    webhook_endpoint_id: UUID = Field(foreign_key="webhook_endpoints.id", index=True)
    status: str = Field(max_length=20)  # "success", "failed", "skipped"
    http_status_code: Optional[int] = None
    error_message: Optional[str] = None
    attempt_number: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
