"""Repair media_items rows created from rsync deletion lines (AC-030).

Used by the Alembic migration that adds ``removed_at``; safe to re-run.
Works on a plain SQLAlchemy connection so it can run before the ORM model
matches the live schema.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.services.media_classifier import classify_transfer_path, parse_rsync_line

logger = logging.getLogger(__name__)

_PHANTOMS = text(
    "SELECT id, path, first_seen_at FROM media_items "
    "WHERE path LIKE 'deleting %' OR path LIKE '*deleting %'"
)
_REAL = text("SELECT id FROM media_items WHERE dedupe_key = :key AND id <> :id")
_RETIRE = text(
    "UPDATE media_items SET removed_at = COALESCE(removed_at, :ts) WHERE id = :id"
)
_DELETE = text("DELETE FROM media_items WHERE id = :id")
_CONVERT = text(
    "UPDATE media_items SET path = :path, kind = :kind, title = :title, "
    "year = :year, season = :season, episode = :episode, dedupe_key = :key, "
    "removed_at = COALESCE(removed_at, :ts) WHERE id = :id"
)


def repair_phantom_media(connection: Connection) -> dict[str, int]:
    """Fold phantom rows into the catalogue.

    - real item exists → retire it at the phantom's ``first_seen_at``, drop phantom
    - no real item → the phantom becomes that (retired) item
    - not classifiable → drop
    """
    counts = {"retired": 0, "converted": 0, "dropped": 0}
    for row in connection.execute(_PHANTOMS).all():
        parsed = parse_rsync_line(row.path)
        match = (
            classify_transfer_path(parsed[1])
            if parsed and parsed[0] == "deletion"
            else None
        )
        if match is None:
            connection.execute(_DELETE, {"id": row.id})
            counts["dropped"] += 1
            continue
        real = connection.execute(
            _REAL, {"key": match.dedupe_key, "id": row.id}
        ).first()
        if real is not None:
            connection.execute(_RETIRE, {"ts": row.first_seen_at, "id": real.id})
            connection.execute(_DELETE, {"id": row.id})
            counts["retired"] += 1
        else:
            connection.execute(
                _CONVERT,
                {
                    "path": match.path[:1024],
                    "kind": match.kind,
                    "title": match.title,
                    "year": match.year,
                    "season": match.season,
                    "episode": match.episode,
                    "key": match.dedupe_key,
                    "ts": row.first_seen_at,
                    "id": row.id,
                },
            )
            counts["converted"] += 1
    if any(counts.values()):
        logger.info("Repaired phantom media items", extra=counts)
    return counts
