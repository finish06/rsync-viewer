"""Media catalogue API — new shows and movies (specs/insight-ui.md AC-018)."""

from datetime import timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import col, select

from app.api.deps import SessionDep, require_role_or_api_key
from app.models.media_item import MediaItem
from app.schemas.media import (
    EpisodeRead,
    MediaNewResponse,
    MediaSummary,
    MovieRead,
    ShowGroup,
)
from app.services.auth import ROLE_VIEWER
from app.utils import utc_now

router = APIRouter(
    prefix="/media",
    tags=["media"],
    dependencies=[Depends(require_role_or_api_key(ROLE_VIEWER))],
)

DaysQuery = Query(7, ge=1, le=90, description="Look-back window in days")


def _recent_items(session: SessionDep, days: int) -> list[MediaItem]:
    cutoff = utc_now() - timedelta(days=days)
    stmt = (
        select(MediaItem)
        .where(col(MediaItem.first_seen_at) >= cutoff)
        .order_by(col(MediaItem.first_seen_at).desc(), col(MediaItem.title))
    )
    return list(session.exec(stmt).all())


def _group_shows(items: list[MediaItem]) -> list[ShowGroup]:
    groups: dict[tuple[str, Optional[int]], ShowGroup] = {}
    for item in items:
        if item.kind != "episode":
            continue
        key = (item.title, item.year)
        group = groups.get(key)
        if group is None:
            group = ShowGroup(title=item.title, year=item.year, new_episodes=[])
            groups[key] = group
        group.new_episodes.append(
            EpisodeRead(
                season=item.season,
                episode=item.episode,
                first_seen_at=item.first_seen_at,
                sync_log_id=item.sync_log_id,
                source_name=item.source_name,
            )
        )
    return list(groups.values())  # insertion order = newest show first


@router.get(
    "/new",
    response_model=MediaNewResponse,
    summary="Shows and movies first seen in the look-back window",
)
async def media_new(
    session: SessionDep,
    days: int = DaysQuery,
    kind: Optional[Literal["show", "movie"]] = Query(None),
) -> MediaNewResponse:
    """Episodes grouped by show, plus movies, newest first."""
    items = _recent_items(session, days)
    shows = _group_shows(items) if kind in (None, "show") else []
    movies = (
        [
            MovieRead(
                title=i.title,
                year=i.year,
                first_seen_at=i.first_seen_at,
                sync_log_id=i.sync_log_id,
                source_name=i.source_name,
            )
            for i in items
            if i.kind == "movie"
        ]
        if kind in (None, "movie")
        else []
    )
    return MediaNewResponse(days=days, shows=shows, movies=movies)


@router.get(
    "/summary",
    response_model=MediaSummary,
    summary="Counts of new movies, shows, and episodes",
)
async def media_summary(session: SessionDep, days: int = DaysQuery) -> MediaSummary:
    """Headline numbers for the Overview 'New this week' panel."""
    items = _recent_items(session, days)
    episodes = [i for i in items if i.kind == "episode"]
    return MediaSummary(
        days=days,
        new_movies=sum(1 for i in items if i.kind == "movie"),
        new_shows=len({(i.title, i.year) for i in episodes}),
        new_episodes=len(episodes),
    )
