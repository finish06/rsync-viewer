"""Back-fill media_items from existing sync logs (specs/insight-ui.md AC-020).

Run via: docker-compose exec app python -m scripts.backfill_media
Idempotent: re-running inserts nothing new.
"""

import logging

from sqlmodel import Session, col, select

from app.models.sync_log import SyncLog
from app.services.media_catalog import record_media
from app.services.synthetic_check import SYNTHETIC_SOURCE_NAME

logger = logging.getLogger(__name__)


def backfill_media(session: Session, batch_size: int = 500) -> int:
    """Walk logs oldest-first so the earliest sighting owns each item."""
    inserted_total = 0
    offset = 0
    while True:
        batch = list(
            session.exec(
                select(SyncLog)
                .where(
                    col(SyncLog.file_list).is_not(None),
                    col(SyncLog.is_dry_run).is_(False),
                    col(SyncLog.source_name) != SYNTHETIC_SOURCE_NAME,
                )
                .order_by(col(SyncLog.start_time), col(SyncLog.id))
                .offset(offset)
                .limit(batch_size)
            ).all()
        )
        if not batch:
            break
        for sync_log in batch:
            inserted_total += record_media(session, sync_log)
        session.commit()
        offset += len(batch)
    return inserted_total


if __name__ == "__main__":
    from app.database import engine

    logging.basicConfig(level=logging.INFO)
    with Session(engine) as db:
        count = backfill_media(db)
    print(f"Back-filled {count} media items")
