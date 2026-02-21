from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FailureEventRead(BaseModel):
    """Schema for failure event response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_name: str
    failure_type: str
    detected_at: datetime
    sync_log_id: Optional[UUID]
    notified: bool
    details: Optional[str]
    created_at: datetime
