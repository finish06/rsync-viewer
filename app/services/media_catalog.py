"""Persist classified media from sync logs (specs/insight-ui.md AC-017)."""

import logging
from uuid import uuid4

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session

from app.models.media_item import MediaItem
from app.models.sync_log import SyncLog
from app.services.media_classifier import classify_file_list
from app.services.synthetic_check import SYNTHETIC_SOURCE_NAME
from app.utils import utc_now

logger = logging.getLogger(__name__)


def record_media(session: Session, sync_log: SyncLog) -> int:
    """Insert any new media items found in ``sync_log.file_list``.

    Returns the number of rows inserted. Existing items (same dedupe key)
    are left untouched so the first sighting keeps its ``first_seen_at``.
    Dry runs and the synthetic source never produce items. Does not commit.
    """
    if sync_log.is_dry_run or sync_log.source_name == SYNTHETIC_SOURCE_NAME:
        return 0
    matches = classify_file_list(sync_log.file_list or [])
    if not matches:
        return 0

    now = utc_now()
    rows = [
        {
            "id": uuid4(),
            "kind": m.kind,
            "title": m.title,
            "year": m.year,
            "season": m.season,
            "episode": m.episode,
            "path": m.path[:1024],
            "source_name": sync_log.source_name,
            "sync_log_id": sync_log.id,
            "first_seen_at": sync_log.start_time,
            "dedupe_key": m.dedupe_key,
            "created_at": now,
        }
        for m in matches
    ]
    # RETURNING yields only the rows actually inserted (conflicts are skipped),
    # which is reliable where rowcount is not for multi-row inserts.
    statement = (
        insert(MediaItem)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["dedupe_key"])
        .returning(MediaItem.id)  # type: ignore[call-overload]
    )
    result = session.exec(statement)  # type: ignore[call-overload]
    return len(result.all())


def record_media_safely(session: Session, sync_log: SyncLog) -> None:
    """Ingest-path wrapper: media classification must never fail a sync log."""
    try:
        inserted = record_media(session, sync_log)
        if inserted:
            session.commit()
            logger.info(
                "Media items recorded",
                extra={"source_name": sync_log.source_name, "inserted": inserted},
            )
    except Exception:
        session.rollback()
        logger.exception(
            "Media classification failed", extra={"sync_log_id": str(sync_log.id)}
        )
