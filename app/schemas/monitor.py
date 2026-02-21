from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MonitorCreate(BaseModel):
    """Schema for creating a sync source monitor."""

    source_name: str = Field(
        ...,
        description="Sync source identifier (matches SyncLog.source_name)",
        examples=["backup-server"],
    )
    expected_interval_hours: int = Field(
        ...,
        gt=0,
        description="Expected sync frequency in hours",
        examples=[24],
    )
    grace_multiplier: float = Field(
        default=1.5,
        gt=0,
        description="Multiplier on interval before flagging stale",
        examples=[1.5],
    )
    enabled: bool = Field(
        default=True,
        description="Whether staleness checking is active",
    )


class MonitorUpdate(BaseModel):
    """Schema for updating a sync source monitor."""

    expected_interval_hours: Optional[int] = Field(
        default=None, gt=0, description="Expected sync frequency in hours"
    )
    grace_multiplier: Optional[float] = Field(
        default=None, gt=0, description="Grace multiplier"
    )
    enabled: Optional[bool] = Field(
        default=None, description="Whether staleness checking is active"
    )


class MonitorRead(BaseModel):
    """Schema for sync source monitor response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_name: str
    expected_interval_hours: int
    grace_multiplier: float
    enabled: bool
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
