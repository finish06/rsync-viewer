from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WebhookCreate(BaseModel):
    """Schema for creating a webhook endpoint."""

    name: str = Field(max_length=100, description="Human-readable name")
    url: str = Field(max_length=2048, description="Target URL for HTTP POST delivery")
    headers: Optional[dict] = Field(
        default=None, description="Custom headers (e.g., Authorization)"
    )
    enabled: bool = Field(default=True, description="Whether endpoint is active")


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook endpoint."""

    name: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = Field(None, max_length=2048)
    headers: Optional[dict] = None
    enabled: Optional[bool] = None


class WebhookRead(BaseModel):
    """Schema for webhook endpoint response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    headers: Optional[dict]
    enabled: bool
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime
