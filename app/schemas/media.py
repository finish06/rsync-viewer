"""Response schemas for the media catalogue API (specs/insight-ui.md AC-018)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class EpisodeRead(BaseModel):
    season: Optional[int]
    episode: Optional[int]
    first_seen_at: datetime
    sync_log_id: Optional[UUID]
    source_name: str


class ShowGroup(BaseModel):
    title: str
    year: Optional[int]
    new_episodes: list[EpisodeRead]


class MovieRead(BaseModel):
    title: str
    year: Optional[int]
    first_seen_at: datetime
    sync_log_id: Optional[UUID]
    source_name: str


class MediaNewResponse(BaseModel):
    days: int
    shows: list[ShowGroup]
    movies: list[MovieRead]


class MediaSummary(BaseModel):
    days: int
    new_movies: int
    new_shows: int
    new_episodes: int
