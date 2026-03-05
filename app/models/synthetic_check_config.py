from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utc_now


class SyntheticCheckConfig(SQLModel, table=True):
    """Singleton DB-backed config for synthetic monitoring (id=1)."""

    __tablename__ = "synthetic_check_config"

    id: int = Field(default=None, primary_key=True)
    enabled: bool = Field(default=False)
    interval_seconds: int = Field(default=300)
    api_key: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
