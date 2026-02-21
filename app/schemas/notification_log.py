from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationLogRead(BaseModel):
    """Schema for notification log response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    failure_event_id: UUID
    webhook_endpoint_id: UUID
    status: str
    http_status_code: Optional[int]
    error_message: Optional[str]
    attempt_number: int
    created_at: datetime
