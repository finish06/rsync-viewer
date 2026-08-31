# Spec: backup & restore tooling

## 1. Overview
Production has real data (sync history, media catalogue, users, settings) and
no backup story. Provide pg_dump-based backups with rotation and a documented,
tested recovery path.

### User Story
As the operator, I want one command (and a cron line) that snapshots the
database with sensible rotation, and a written recovery procedure I can follow
under stress.

## 2. Acceptance Criteria
| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | `python -m scripts.backup` produces a timestamped `pg_dump` custom-format archive (`backups/rsync-viewer-YYYYMMDD-HHMMSS.dump`) using `DATABASE_URL` (CLI/env overridable directory). Exit code non-zero and no partial file left on failure. | Must |
| AC-002 | Rotation: `--keep N` (default 14) deletes the oldest archives beyond N after a successful dump; only files matching the tool's own naming pattern are ever deleted. | Must |
| AC-003 | `python -m scripts.restore <archive>` runs `pg_restore --clean --if-exists` into `DATABASE_URL`; it refuses to run without an explicit `--yes` and prints what it will do first. | Must |
| AC-004 | A recovery runbook (`docs/backup-restore.md`) documents: taking a backup, scheduling (host cron + docker compose exec example), full restore, and restore-to-a-scratch-database verification; README links it. | Must |
| AC-005 | `backups/` is gitignored; the tools never log credentials (password stays inside the URL/env, echoed nowhere). | Must |

## 3. User Test Cases
- **TC-001** Run backup twice with `--keep 1` → one archive remains, it is a valid `pg_restore --list`-able file.
- **TC-002** Restore the archive into a scratch database → row counts match the source for `sync_logs`, `users`, `media_items`.
- **TC-003** Backup with an unreachable DB → non-zero exit, no file left behind.

## 4. Edge Cases
- `pg_dump` missing on the host → clear error naming the dependency (documented: run via the app container, which ships pg client tools — verified in the runbook).
- Backup directory does not exist → created.
- `--keep 0` → refused (would delete the backup just taken).
