# Plan: backup & restore + synthetic hygiene

**Specs:** specs/backup-restore.md, specs/synthetic-hygiene.md · **Branch:** `feature/backup-and-synthetic-hygiene` · **Release:** v2.22.0 (`feat:` → minor; CHANGELOG carries Added + Fixed)

## Tasks
| # | Task | Files | AC |
|---|------|-------|----|
| T1 | `scripts/backup.py`: pg_dump -Fc, timestamped file, `--keep` rotation (own-pattern only), no-partial-on-failure | `scripts/backup.py` | B/AC-001,002,005 |
| T2 | `scripts/restore.py`: pg_restore --clean --if-exists, `--yes` gate | `scripts/restore.py` | B/AC-003 |
| T3 | Runbook + README link + `.gitignore` `backups/` | `docs/backup-restore.md`, README, .gitignore | B/AC-004,005 |
| T4 | In-process cleanup delete replaces the HTTP DELETE in `run_synthetic_check` | `app/services/synthetic_check.py` | S/AC-001 |
| T5 | `_wait_until_healthy()` warm-up before the first check; no events during warm-up | `app/services/synthetic_check.py` | S/AC-002 |
| T6 | `cleanup_synthetic_logs(session)` (older than 1 h) — called at monitor start and from the retention pass | `app/services/retention.py`, `synthetic_check.py` | S/AC-003,004 |
| T7 | Tests RED-first: backup rotation/failure/keep-guard, restore gate; synthetic no-leak, warm-up no-webhook, purge selectivity | `tests/test_backup_restore.py`, `tests/test_synthetic_v2.py` | all |

## QA
Full suites; local stack: restart app → no failure webhook logged, synthetic row count flat across a cycle; run backup + restore into a scratch DB on the local postgres and diff row counts (TC-002 of backup spec).
