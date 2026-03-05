from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils import utc_now


class SyntheticCheckResultRecord(SQLModel, table=True):
    """Time-series record of synthetic check results, auto-pruned to 100 rows."""

    __tablename__ = "synthetic_check_results"

    id: int = Field(default=None, primary_key=True)
    checked_at: datetime = Field(default_factory=utc_now, index=True)
    status: str = Field(max_length=20)  # "passing" or "failing"
    latency_ms: float = Field(default=0.0)
    error: Optional[str] = Field(default=None)
