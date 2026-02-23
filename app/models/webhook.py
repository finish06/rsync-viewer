from datetime import datetime
from app.utils import utc_now
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


class WebhookEndpoint(SQLModel, table=True):
    __tablename__ = "webhook_endpoints"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100)
    url: str = Field(max_length=2048)
    headers: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    webhook_type: str = Field(default="generic", max_length=20)
    source_filters: Optional[list] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    enabled: bool = Field(default=True, index=True)
    consecutive_failures: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
