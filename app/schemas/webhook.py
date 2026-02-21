import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

DISCORD_URL_PATTERN = re.compile(
    r"^https://(discord\.com|discordapp\.com)/api/webhooks/\d+/.+"
)


class WebhookCreate(BaseModel):
    """Schema for creating a webhook endpoint."""

    name: str = Field(max_length=100, description="Human-readable name")
    url: str = Field(max_length=2048, description="Target URL for HTTP POST delivery")
    headers: Optional[dict] = Field(
        default=None, description="Custom headers (e.g., Authorization)"
    )
    webhook_type: str = Field(
        default="generic", description="Webhook type: 'generic' or 'discord'"
    )
    source_filters: Optional[list[str]] = Field(
        default=None, description="Source names to filter on (null = all)"
    )
    options: Optional[dict] = Field(
        default=None, description="Type-specific options (e.g., Discord embed config)"
    )
    enabled: bool = Field(default=True, description="Whether endpoint is active")

    @model_validator(mode="after")
    def validate_discord_url(self):
        if self.webhook_type == "discord" and not DISCORD_URL_PATTERN.match(self.url):
            raise ValueError(
                "Discord webhooks require a URL matching "
                "https://discord.com/api/webhooks/... or "
                "https://discordapp.com/api/webhooks/..."
            )
        return self


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook endpoint."""

    name: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = Field(None, max_length=2048)
    headers: Optional[dict] = None
    webhook_type: Optional[str] = None
    source_filters: Optional[list[str]] = None
    options: Optional[dict] = None
    enabled: Optional[bool] = None


class WebhookRead(BaseModel):
    """Schema for webhook endpoint response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    headers: Optional[dict]
    webhook_type: str
    source_filters: Optional[list[str]]
    options: Optional[dict] = None
    enabled: bool
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime
