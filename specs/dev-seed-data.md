# Spec: Dev Seed Data

**Version:** 0.1.0
**Created:** 2026-02-24
**PRD Reference:** docs/prd.md
**Status:** Draft
**Milestone:** M11 — Polish & Infrastructure

## 1. Overview

Provide a `docker-compose.seed.yml` override file and a SQL seed script that populates a fresh PostgreSQL database with realistic rsync log data. Developers run `docker-compose -f docker-compose.yml -f docker-compose.seed.yml up -d` to get a fully populated dev environment with sync logs, webhooks, API keys, and notification history — ready for UI development and manual testing.

### User Story

As a developer, I want a one-command dev environment with realistic seed data, so that I can develop and test features without manually creating test data.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A `docker-compose.seed.yml` file exists that overrides the `db` service to mount a SQL seed script into `/docker-entrypoint-initdb.d/` | Must |
| AC-002 | The seed script creates ~50 sync log entries across 3 sources ("photos", "videos", "files") spanning the last 30 days | Must |
| AC-003 | Seed data includes realistic rsync raw output with parsed statistics (bytes, speed, file counts, speedup ratios) | Must |
| AC-004 | Seed data includes 5 failed syncs (non-zero exit codes, error status) distributed across sources | Must |
| AC-005 | Seed data includes a mix of dry runs and real syncs | Must |
| AC-006 | Seed data includes 2 webhook endpoints: 1 Discord-type and 1 generic (Home Assistant) | Must |
| AC-007 | Seed data includes 1 active API key with a known dev key value | Must |
| AC-008 | Running `docker-compose -f docker-compose.yml -f docker-compose.seed.yml up -d` with a fresh volume produces a populated database | Must |
| AC-009 | Seed script is idempotent — it only runs on initial database creation (Postgres initdb behavior) | Should |
| AC-010 | Seed data includes notification history entries for the failed syncs | Should |

## 3. User Test Cases

### TC-001: Fresh dev environment with seed data

**Precondition:** No existing `postgres_data` volume (or volume removed with `docker-compose down -v`)
**Steps:**
1. Run `docker-compose -f docker-compose.yml -f docker-compose.seed.yml up -d`
2. Wait for services to be healthy
3. Navigate to http://localhost:8000
**Expected Result:** Dashboard shows sync logs from 3 sources (photos, videos, files) with charts populated. Some entries show failed status. Filtering by source shows entries for each source.
**Screenshot Checkpoint:** N/A (infrastructure feature)
**Maps to:** TBD

### TC-002: Webhooks visible in settings

**Precondition:** Dev environment running with seed data
**Steps:**
1. Navigate to http://localhost:8000/settings
2. Observe the Webhooks section
**Expected Result:** Two webhooks are listed: one Discord webhook and one Home Assistant webhook.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-003: Seed does not re-run on restart

**Precondition:** Dev environment previously started with seed data
**Steps:**
1. Run `docker-compose -f docker-compose.yml -f docker-compose.seed.yml down`
2. Run `docker-compose -f docker-compose.yml -f docker-compose.seed.yml up -d`
**Expected Result:** Database retains original seed data without duplication. Row counts remain the same.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

## 4. Data Model

No new models. Seed data populates existing tables:

### sync_logs

~50 rows with realistic data:
- 3 sources: "photos", "videos", "files"
- Dates spanning last 30 days (roughly daily syncs per source)
- ~45 successful (exit_code=0, status="completed"), ~5 failed (exit_code=23/24, status="failed")
- ~5 dry runs (is_dry_run=true)
- Realistic raw_content with rsync output
- Parsed stats: total_size_bytes, bytes_sent, bytes_received, transfer_speed, speedup_ratio, file_count

### webhook_endpoints

2 rows:
- "Discord Alerts" — webhook_type="discord", url="https://discord.com/api/webhooks/example/token", enabled=true
- "Home Assistant" — webhook_type="generic", url="http://homeassistant.local:8123/api/webhook/rsync-alerts", enabled=true

### api_keys

1 row:
- name="dev-key", key_hash=bcrypt hash of DEFAULT_API_KEY, key_prefix="rsv_dev_k", is_active=true

### Relationships

Notification history entries reference webhook_endpoint IDs and sync_log IDs for the failed syncs.

## 5. API Contract

N/A — this is an infrastructure/tooling feature with no new endpoints.

## 6. UI Behavior

N/A — no UI changes. Seed data is consumed by existing UI.

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Volume already exists with data | Postgres skips `/docker-entrypoint-initdb.d/` scripts — no duplication |
| Seed script SQL syntax error | Container fails to start; developer sees error in `docker-compose logs db` |
| Schema changes after seed script written | Seed script may need updating; document this in script header comment |
| Running without seed override | `docker-compose up -d` works as before with empty database |
| DEFAULT_API_KEY env var not set | Seed script uses a hardcoded dev key hash as fallback |

## 8. Dependencies

- Existing `docker-compose.yml` with `db` service
- Existing SQLModel table schemas (sync_logs, webhook_endpoints, api_keys)
- Postgres 16 `/docker-entrypoint-initdb.d/` convention
- bcrypt hash for the dev API key must match `app/api/deps.py` verification logic

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-24 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
