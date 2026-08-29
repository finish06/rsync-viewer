# Plan: rsync deletion lines in the media catalogue

**Spec:** specs/insight-ui.md AC-028–AC-030, TC-008 · **Branch:** `fix/media-rsync-deletions` · **Release:** v2.15.1 (`fix:` → patch)

## Why
The production `scripts.backfill_media` run created phantom `media_items` rows from rsync `deleting …` lines: the parser keeps any line containing `/` in `file_list`, and the classifier treated `deleting Movies/Title (Year)/file.mkv` as a movie under a `deleting Movies` folder. Four rows (Bloodlands-style) exist with no real counterpart because the media was deleted before the catalogue existed.

## Tasks
| # | Task | Files | AC |
|---|------|-------|----|
| T1 | `parse_rsync_line()` — recognise deletion / itemized / control lines; `classify_file_list` only classifies transfers | `app/services/media_classifier.py` | AC-028 |
| T2 | `MediaItem.removed_at`; `record_media` applies deletions first (item + directory prefix), un-retires re-transferred items, then inserts | `app/models/media_item.py`, `app/services/media_catalog.py` | AC-029 |
| T3 | `/media/new` and `/media/summary` exclude retired rows | `app/api/endpoints/media.py` | AC-029 |
| T4 | `repair_phantom_media(connection)` + Alembic migration (column + repair) | `app/services/media_repair.py`, `alembic/versions/*_add_media_removed_at.py` | AC-030 |
| T5 | CHANGELOG 2.15.1; note to re-run the backfill after deploy | `CHANGELOG.md` | AC-030 |

## Test strategy (RED first)
- `tests/test_media_classifier.py`: parametrised control-line cases, itemized transfer cases, `parse_rsync_line` contract.
- `tests/test_media_items.py`: deletion retires, directory deletion retires by prefix within the source, re-transfer un-retires keeping `first_seen_at`, API excludes retired, repair of phantom rows (with and without a real counterpart).

## Dependencies / risks
- Alembic migration imports the classifier (pure Python) to recompute dedupe keys — acceptable; no DB access outside the migration connection.
- `file_count` / `file_list` on sync logs are untouched (Transfers page unchanged); only the media catalogue interprets control lines.
