from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

from app.utils import utc_now


class MediaItem(SQLModel, table=True):
    """A movie or TV episode first seen in a sync's file list (specs/insight-ui.md §4).

    Items outlive their sync log: the FK is nulled when retention deletes the log.
    """

    __tablename__ = "media_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    kind: str = Field(max_length=10)  # "movie" | "episode"
    title: str = Field(max_length=200, index=True)
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    path: str = Field(max_length=1024)
    source_name: str = Field(max_length=100, index=True)
    sync_log_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("sync_logs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    first_seen_at: datetime = Field(index=True)
    # Set when rsync reported the file (or its directory) deleted; cleared on
    # re-transfer. Retired items are hidden from "new" views (AC-029).
    removed_at: Optional[datetime] = Field(default=None, index=True)
    dedupe_key: str = Field(max_length=300, unique=True)
    created_at: datetime = Field(default_factory=utc_now)
