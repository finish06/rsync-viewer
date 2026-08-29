"""Tests for the media catalogue store — specs/insight-ui.md AC-017, AC-020, AC-021."""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from app.models.media_item import MediaItem
from app.models.sync_log import SyncLog
from app.services.media_catalog import record_media
from app.services.synthetic_check import SYNTHETIC_SOURCE_NAME
from app.utils import utc_now
from scripts.backfill_media import backfill_media

RSYNC_TAIL = (
    "\nsent 2.87K bytes  received 291.07K bytes  117.58K bytes/sec\n"
    "total size is 18.70G  speedup is 63.94"
)
MEDIA_PATHS = [
    "The Polar Express (2004)/The Polar Express.2004.Bluray-1080p.EAC3.x265.mkv",
    "The Polar Express (2004)/The Polar Express.2004.Bluray-1080p.EAC3.x265.en.srt",
    "Severance (2022)/Season 02/Severance - S02E03 - Who Is Alive.mkv",
]


def _payload(source: str = "media", dry_run: bool = False) -> dict:
    now = utc_now()
    tail = RSYNC_TAIL + (" (DRY RUN)" if dry_run else "")
    return {
        "source_name": source,
        "start_time": (now - timedelta(minutes=3)).isoformat(),
        "end_time": now.isoformat(),
        "raw_content": "receiving file list ... done\n" + "\n".join(MEDIA_PATHS) + tail,
        "exit_code": 0,
    }


@pytest.fixture(autouse=True)
def clean_media(db_session: Session):
    for row in db_session.exec(select(MediaItem)).all():
        db_session.delete(row)
    db_session.commit()


def _items(db_session: Session) -> list[MediaItem]:
    return list(db_session.exec(select(MediaItem).order_by(MediaItem.title)).all())


class TestAC017IngestHook:
    async def test_ac017_ingest_creates_items_once(self, client, db_session):
        resp = await client.post("/api/v1/sync-logs", json=_payload())
        assert resp.status_code == 201
        log_id = resp.json()["id"]

        items = _items(db_session)
        assert [(i.kind, i.title, i.year, i.season, i.episode) for i in items] == [
            ("episode", "Severance", 2022, 2, 3),
            ("movie", "The Polar Express", 2004, None, None),
        ]
        assert all(str(i.sync_log_id) == log_id for i in items)
        assert all(i.source_name == "media" for i in items)
        assert items[0].first_seen_at is not None

        # Re-syncing the same files never duplicates
        resp = await client.post("/api/v1/sync-logs", json=_payload())
        assert resp.status_code == 201
        again = _items(db_session)
        assert len(again) == 2
        assert all(str(i.sync_log_id) == log_id for i in again)  # first sighting wins

    async def test_ac021_dry_run_and_synthetic_skipped(self, client, db_session):
        assert (
            await client.post("/api/v1/sync-logs", json=_payload(dry_run=True))
        ).status_code == 201
        assert (
            await client.post(
                "/api/v1/sync-logs", json=_payload(source=SYNTHETIC_SOURCE_NAME)
            )
        ).status_code == 201
        assert _items(db_session) == []

    async def test_ac021_no_media_is_fine(self, client, db_session):
        payload = _payload()
        payload["raw_content"] = (
            "receiving file list ... done\nPhotos/a.jpg" + RSYNC_TAIL
        )
        assert (await client.post("/api/v1/sync-logs", json=payload)).status_code == 201
        assert _items(db_session) == []


class TestAC017Retention:
    def test_ac017_items_survive_sync_log_deletion(self, db_session, create_sync_log):
        log = create_sync_log(source_name="media", file_list=MEDIA_PATHS)
        assert record_media(db_session, log) == 2
        db_session.commit()

        db_session.delete(db_session.get(SyncLog, log.id))
        db_session.commit()

        items = _items(db_session)
        assert len(items) == 2
        assert all(i.sync_log_id is None for i in items)


class TestAC020Backfill:
    def test_ac020_backfill_is_idempotent(self, db_session, create_sync_log):
        now = utc_now()
        create_sync_log(
            source_name="media",
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2) + timedelta(minutes=1),
            file_list=MEDIA_PATHS[:1],
        )
        create_sync_log(source_name="media", file_list=MEDIA_PATHS)
        create_sync_log(source_name="media", file_list=MEDIA_PATHS, is_dry_run=True)
        create_sync_log(source_name=SYNTHETIC_SOURCE_NAME, file_list=MEDIA_PATHS)
        create_sync_log(source_name="photos", file_list=["Photos/a.jpg"])

        assert backfill_media(db_session, batch_size=2) == 2
        items = {i.title: i for i in _items(db_session)}
        # oldest log wins first_seen_at for the movie
        assert (
            items["The Polar Express"].first_seen_at.date()
            == (now - timedelta(days=2)).date()
        )
        assert items["Severance"].first_seen_at.date() == now.date()

        assert backfill_media(db_session) == 0
        assert len(_items(db_session)) == 2


# ---------------------------------------------------------------------------
# AC-029: deletions retire items; AC-030: phantom repair
# ---------------------------------------------------------------------------

from app.services.media_classifier import classify_path  # noqa: E402
from app.services.media_repair import repair_phantom_media  # noqa: E402

MOVIE = "Movies/The Polar Express (2004)/The Polar Express (2004).mkv"
EPISODE = "TV/Severance (2022)/Season 02/Severance - S02E03 - Who Is Alive.mkv"
EPISODE_2 = "TV/Severance (2022)/Season 02/Severance - S02E04 - Woe's Hollow.mkv"


class TestAC029Deletions:
    def test_ac029_deletion_line_retires_item(self, db_session, create_sync_log):
        now = utc_now()
        first = create_sync_log(
            source_name="media",
            start_time=now - timedelta(days=3),
            file_list=[MOVIE, EPISODE],
        )
        assert record_media(db_session, first) == 2
        deletion = create_sync_log(
            source_name="media",
            start_time=now - timedelta(days=1),
            file_list=[f"deleting {MOVIE}", "sending incremental file list"],
        )
        assert record_media(db_session, deletion) == 0
        db_session.commit()

        items = {i.title: i for i in _items(db_session)}
        assert items["The Polar Express"].removed_at is not None
        assert (
            items["The Polar Express"].removed_at.date()
            == (now - timedelta(days=1)).date()
        )
        assert (
            items["The Polar Express"].first_seen_at.date()
            == (now - timedelta(days=3)).date()
        )
        assert items["Severance"].removed_at is None

    def test_ac029_directory_deletion_retires_by_prefix_within_source(
        self, db_session, create_sync_log
    ):
        record_media(
            db_session,
            create_sync_log(source_name="media", file_list=[EPISODE, EPISODE_2, MOVIE]),
        )
        record_media(
            db_session,
            create_sync_log(source_name="mirror", file_list=[EPISODE]),
        )
        # mirror's episode has the same dedupe key → only one row exists, owned by "media"
        record_media(
            db_session,
            create_sync_log(
                source_name="media",
                file_list=["*deleting   TV/Severance (2022)/Season 02/"],
            ),
        )
        db_session.commit()
        by_path = {i.path: i for i in _items(db_session)}
        assert by_path[EPISODE].removed_at is not None
        assert by_path[EPISODE_2].removed_at is not None
        assert by_path[MOVIE].removed_at is None

        # A directory deletion from another source does not touch these paths
        record_media(
            db_session,
            create_sync_log(source_name="photos", file_list=["deleting Movies/"]),
        )
        db_session.commit()
        assert {i.path: i for i in _items(db_session)}[MOVIE].removed_at is None

    def test_ac029_retransfer_unretires_keeping_first_seen(
        self, db_session, create_sync_log
    ):
        now = utc_now()
        record_media(
            db_session,
            create_sync_log(
                source_name="media",
                start_time=now - timedelta(days=5),
                file_list=[MOVIE],
            ),
        )
        record_media(
            db_session,
            create_sync_log(source_name="media", file_list=[f"deleting {MOVIE}"]),
        )
        # deletions apply before transfers inside one log
        assert (
            record_media(
                db_session,
                create_sync_log(
                    source_name="media", file_list=[f"deleting {MOVIE}", MOVIE]
                ),
            )
            == 0
        )
        db_session.commit()
        item = _items(db_session)[0]
        assert item.removed_at is None
        assert item.first_seen_at.date() == (now - timedelta(days=5)).date()

    async def test_ac029_api_excludes_retired(self, client, db_session):
        payload = _payload()
        payload["raw_content"] = (
            "receiving file list ... done\n"
            f"deleting {MOVIE}\n{MOVIE}\n{EPISODE}\n" + RSYNC_TAIL
        )
        assert (await client.post("/api/v1/sync-logs", json=payload)).status_code == 201
        summary = (await client.get("/api/v1/media/summary?days=7")).json()
        assert (summary["new_movies"], summary["new_episodes"]) == (1, 1)

        payload["raw_content"] = (
            "receiving file list ... done\n"
            f"deleting {MOVIE}\ndeleting TV/Severance (2022)/\n" + RSYNC_TAIL
        )
        assert (await client.post("/api/v1/sync-logs", json=payload)).status_code == 201
        summary = (await client.get("/api/v1/media/summary?days=7")).json()
        assert (
            summary["new_movies"],
            summary["new_shows"],
            summary["new_episodes"],
        ) == (
            0,
            0,
            0,
        )
        new = (await client.get("/api/v1/media/new?days=7")).json()
        assert new["movies"] == [] and new["shows"] == []


def _phantom(db_session: Session, raw_line: str, first_seen_at) -> MediaItem:
    """Insert a row the old classifier would have produced from a deletion line."""
    match = classify_path(raw_line.split(" ", 1)[1].strip())
    assert match is not None
    row = MediaItem(
        kind=match.kind,
        title="deleting " + match.title if match.kind == "movie" else match.title,
        year=match.year,
        season=match.season,
        episode=match.episode,
        path=raw_line,
        source_name="media",
        first_seen_at=first_seen_at,
        dedupe_key="phantom|" + match.dedupe_key,
    )
    db_session.add(row)
    db_session.commit()
    return row


class TestAC030PhantomRepair:
    def test_ac030_phantom_with_real_row_retires_real_and_is_deleted(
        self, db_session, create_sync_log
    ):
        now = utc_now()
        record_media(
            db_session,
            create_sync_log(
                source_name="media",
                start_time=now - timedelta(days=9),
                file_list=[MOVIE],
            ),
        )
        db_session.commit()
        phantom_id = _phantom(
            db_session, f"deleting {MOVIE}", now - timedelta(days=2)
        ).id

        counts = repair_phantom_media(db_session.connection())
        db_session.commit()
        db_session.expire_all()

        assert counts == {"retired": 1, "converted": 0, "dropped": 0}
        items = _items(db_session)
        assert len(items) == 1
        assert items[0].id != phantom_id
        assert items[0].path == MOVIE
        assert items[0].removed_at.date() == (now - timedelta(days=2)).date()
        assert items[0].first_seen_at.date() == (now - timedelta(days=9)).date()

    def test_ac030_phantom_without_real_row_becomes_retired_item(self, db_session):
        now = utc_now()
        phantom = _phantom(db_session, f"deleting {EPISODE}", now - timedelta(days=4))
        _phantom(db_session, "*deleting   " + MOVIE, now - timedelta(days=1))

        counts = repair_phantom_media(db_session.connection())
        db_session.commit()
        db_session.expire_all()

        assert counts == {"retired": 0, "converted": 2, "dropped": 0}
        by_path = {i.path: i for i in _items(db_session)}
        episode = by_path[EPISODE]
        assert episode.id == phantom.id
        assert (episode.title, episode.season, episode.episode) == ("Severance", 2, 3)
        assert episode.dedupe_key == classify_path(EPISODE).dedupe_key
        assert episode.removed_at.date() == (now - timedelta(days=4)).date()
        assert by_path[MOVIE].title == "The Polar Express"
        assert by_path[MOVIE].removed_at is not None

        # idempotent
        assert repair_phantom_media(db_session.connection()) == {
            "retired": 0,
            "converted": 0,
            "dropped": 0,
        }

    def test_ac030_unclassifiable_phantom_is_dropped(self, db_session):
        row = MediaItem(
            kind="movie",
            title="deleting Movies",
            year=None,
            path="deleting Movies/readme.txt",
            source_name="media",
            first_seen_at=utc_now(),
            dedupe_key="movie|deleting movies|None|None|None",
        )
        db_session.add(row)
        db_session.commit()
        assert repair_phantom_media(db_session.connection()) == {
            "retired": 0,
            "converted": 0,
            "dropped": 1,
        }
        db_session.commit()
        assert _items(db_session) == []
