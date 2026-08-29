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
