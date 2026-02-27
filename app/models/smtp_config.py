from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.utils import utc_now


class SmtpConfig(SQLModel, table=True):
    __tablename__ = "smtp_config"

    id: int = Field(default=None, primary_key=True)
    host: str = Field(max_length=255)
    port: int
    username: Optional[str] = Field(default=None, max_length=255)
    encrypted_password: Optional[str] = Field(default=None)
    encryption: str = Field(default="starttls", max_length=20)
    from_address: str = Field(max_length=255)
    from_name: str = Field(default="Rsync Viewer", max_length=255)
    enabled: bool = Field(default=True)
    configured_by_id: Optional[UUID] = Field(
        default=None, foreign_key="users.id", index=True
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
