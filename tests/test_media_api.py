"""Tests for GET /api/v1/media/* — specs/insight-ui.md AC-018."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.models.media_item import MediaItem
from app.models.user import User
from app.services.auth import ROLE_VIEWER, hash_password
from app.utils import utc_now
from tests.test_rbac import _make_bearer_client, _make_unauth_client


@pytest.fixture(autouse=True)
def clean_media(db_session: Session):
    for row in db_session.exec(select(MediaItem)).all():
        db_session.delete(row)
    db_session.commit()


@pytest.fixture
def viewer_user(db_session: Session) -> User:
    user = User(
        username="media_viewer",
        email="media_viewer@test.com",
        password_hash=hash_password("ViewPass1!"),
        role=ROLE_VIEWER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _item(
    kind, title, year=None, season=None, episode=None, days_ago=0, source="media"
):
    return MediaItem(
        id=uuid4(),
        kind=kind,
        title=title,
        year=year,
        season=season,
        episode=episode,
        path=f"{title}/{title}.mkv",
        source_name=source,
        sync_log_id=None,
        first_seen_at=utc_now() - timedelta(days=days_ago),
        dedupe_key=f"{kind}|{title.lower()}|{year}|{season}|{episode}",
    )


@pytest.fixture
def seeded(db_session: Session):
    rows = [
        _item("episode", "Severance", 2022, 2, 3, days_ago=1),
        _item("episode", "Severance", 2022, 2, 2, days_ago=2),
        _item("episode", "Slow Horses", None, 4, 5, days_ago=3),
        _item("episode", "Dark", None, 1, 1, days_ago=20),  # outside 7d
        _item("movie", "The Polar Express", 2004, days_ago=0),
        _item("movie", "Heat", 1995, days_ago=6),
        _item("movie", "Old Film", 1980, days_ago=30),  # outside 7d
    ]
    db_session.add_all(rows)
    db_session.commit()
    return rows


class TestAC018MediaNew:
    async def test_ac018_groups_shows_and_lists_movies(self, client, seeded):
        resp = await client.get("/api/v1/media/new?days=7")
        assert resp.status_code == 200
        body = resp.json()
        assert body["days"] == 7

        shows = body["shows"]
        assert [s["title"] for s in shows] == ["Severance", "Slow Horses"]
        severance = shows[0]
        assert severance["year"] == 2022
        assert [(e["season"], e["episode"]) for e in severance["new_episodes"]] == [
            (2, 3),
            (2, 2),
        ]
        assert set(severance["new_episodes"][0]) == {
            "season",
            "episode",
            "first_seen_at",
            "sync_log_id",
            "source_name",
        }

        movies = body["movies"]
        assert [(m["title"], m["year"]) for m in movies] == [
            ("The Polar Express", 2004),
            ("Heat", 1995),
        ]

    async def test_ac018_kind_filter_and_window(self, client, seeded):
        only_movies = (await client.get("/api/v1/media/new?days=7&kind=movie")).json()
        assert only_movies["shows"] == []
        assert len(only_movies["movies"]) == 2

        only_shows = (await client.get("/api/v1/media/new?days=7&kind=show")).json()
        assert only_shows["movies"] == []
        assert len(only_shows["shows"]) == 2

        wide = (await client.get("/api/v1/media/new?days=60")).json()
        assert [m["title"] for m in wide["movies"]] == [
            "The Polar Express",
            "Heat",
            "Old Film",
        ]
        assert (await client.get("/api/v1/media/new?days=0")).status_code == 422
        assert (await client.get("/api/v1/media/new?kind=song")).status_code == 422

    async def test_ac018_summary_counts(self, client, seeded):
        body = (await client.get("/api/v1/media/summary?days=7")).json()
        assert body == {
            "days": 7,
            "new_movies": 2,
            "new_shows": 2,
            "new_episodes": 3,
        }

    async def test_ac018_requires_auth(self, db_session, viewer_user, seeded):
        assert (
            await _make_unauth_client(db_session).get("/api/v1/media/new")
        ).status_code == 401
        assert (
            await _make_bearer_client(db_session, viewer_user).get(
                "/api/v1/media/summary"
            )
        ).status_code == 200
