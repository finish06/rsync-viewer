from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


class WebhookOptions(SQLModel, table=True):
    __tablename__ = "webhook_options"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    webhook_endpoint_id: UUID = Field(
        sa_column=Column(
            "webhook_endpoint_id",
            ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
            unique=True,
            index=True,
            nullable=False,
        )
    )
    options: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
