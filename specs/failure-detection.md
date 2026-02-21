# Spec: Failure Detection

**Version:** 0.1.0
**Created:** 2026-02-21
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Detect failed rsync syncs via non-zero exit codes and stale sync detection — when a source hasn't synced within its configured expected interval (with a 1.5x grace multiplier) — and flag them for the notification system to act on.

### User Story

As a homelab administrator, I want to be notified of failed or stale syncs automatically, so that I don't have to load the dashboard to check.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A sync log submitted with a non-zero exit code is marked as "failed" and creates a FailureEvent | Must |
| AC-002 | Each sync source can have a configurable expected sync frequency (in hours) | Must |
| AC-003 | A background scheduler periodically checks for stale sources that haven't synced within `expected_interval * 1.5` | Must |
| AC-004 | Stale sources generate a FailureEvent with failure_type "stale" | Must |
| AC-005 | Failure and stale status is visible on the dashboard sync table | Must |
| AC-006 | Sync source frequency configuration is manageable through the dashboard UI | Must |
| AC-007 | CRUD API endpoints exist for sync source monitors at `/api/v1/monitors` | Must |
| AC-008 | GET endpoint exists for failure events at `/api/v1/failures` | Must |
| AC-009 | Sources without a configured frequency are not checked for staleness | Must |
| AC-010 | The grace multiplier defaults to 1.5 but is configurable per source | Should |
| AC-011 | Existing sync logs without exit codes are treated as successful (backward compatibility) | Must |

## 3. User Test Cases

### TC-001: Failed sync detected via exit code

**Precondition:** App is running, API key configured, at least one previous successful sync exists
**Steps:**
1. Submit a sync log via POST `/api/v1/sync-logs` with `exit_code: 1`
2. Navigate to the dashboard sync table
3. Observe the sync log entry
**Expected Result:** The sync log appears with a "failed" indicator. A FailureEvent is created with `failure_type: "exit_code"`.
**Screenshot Checkpoint:** tests/screenshots/failure-detection/step-01-failed-sync-in-table.png
**Maps to:** TBD

### TC-002: Stale sync detected

**Precondition:** A sync source monitor is configured with `expected_interval_hours: 24`. Last sync was 37 hours ago (exceeds 24 * 1.5 = 36 hour grace window).
**Steps:**
1. Background scheduler runs its periodic check
2. Navigate to the dashboard
3. Observe the source status
**Expected Result:** A FailureEvent with `failure_type: "stale"` is created. The dashboard shows a stale warning for that source.
**Screenshot Checkpoint:** tests/screenshots/failure-detection/step-02-stale-source-warning.png
**Maps to:** TBD

### TC-003: Configure sync source monitor via dashboard

**Precondition:** App is running, user is on the dashboard
**Steps:**
1. Navigate to the sync source monitors configuration
2. Add a new monitor: source_name "backup-server", expected_interval_hours 24
3. Save the configuration
**Expected Result:** Monitor is created and visible in the list. Source will be checked for staleness on the next scheduler cycle.
**Screenshot Checkpoint:** tests/screenshots/failure-detection/step-03-monitor-config-ui.png
**Maps to:** TBD

### TC-004: Source within grace period is not flagged

**Precondition:** Monitor configured with `expected_interval_hours: 24`. Last sync was 30 hours ago (within 36-hour grace window).
**Steps:**
1. Background scheduler runs its periodic check
**Expected Result:** No FailureEvent is created. Source is not flagged as stale.
**Screenshot Checkpoint:** N/A (backend-only behavior)
**Maps to:** TBD

### TC-005: Configure monitor via API

**Precondition:** App is running, API key configured
**Steps:**
1. POST `/api/v1/monitors` with `{"source_name": "nas-backup", "expected_interval_hours": 168, "enabled": true}`
2. GET `/api/v1/monitors`
**Expected Result:** Monitor is created and returned in the list with default `grace_multiplier: 1.5`.
**Screenshot Checkpoint:** N/A (API-only)
**Maps to:** TBD

## 4. Data Model

### SyncLog (existing — modification)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| exit_code | Integer | No | Rsync process exit code. Null for existing logs (backward compat). Non-zero = failure. |

### SyncSourceMonitor (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| source_name | String | Yes | Unique sync source identifier (matches SyncLog.source_name) |
| expected_interval_hours | Integer | Yes | How often this source should sync (e.g., 24, 168, 336) |
| grace_multiplier | Float | No | Multiplier on interval before flagging stale. Default 1.5 |
| enabled | Boolean | Yes | Whether staleness checking is active for this source. Default true |
| last_sync_at | DateTime | No | Timestamp of most recent sync from this source (denormalized for fast checks) |
| created_at | DateTime | Yes | Record creation timestamp |
| updated_at | DateTime | Yes | Last modification timestamp |

### FailureEvent (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| source_name | String | Yes | Which sync source failed or went stale |
| failure_type | String | Yes | Enum: "exit_code" or "stale" |
| detected_at | DateTime | Yes | When the failure was detected |
| sync_log_id | UUID (FK) | No | Reference to the failed SyncLog. Null for stale failures. |
| notified | Boolean | Yes | Whether downstream notification has been sent. Default false |
| details | String | No | Human-readable failure description (e.g., "Exit code 23" or "No sync in 37 hours, expected every 24 hours") |
| created_at | DateTime | Yes | Record creation timestamp |

### Relationships

- `FailureEvent.sync_log_id` → `SyncLog.id` (optional FK, null for stale-type failures)
- `SyncSourceMonitor.source_name` matches `SyncLog.source_name` (logical relationship, not FK — sources appear dynamically from incoming logs)

## 5. API Contract

### POST /api/v1/sync-logs (modification)

**Description:** Existing endpoint — now accepts optional `exit_code` field.

**Request (additional field):**
```json
{
  "exit_code": 1
}
```

If `exit_code` is non-zero, a FailureEvent is automatically created after the sync log is stored.

### GET /api/v1/monitors

**Description:** List all sync source monitors.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "source_name": "backup-server",
    "expected_interval_hours": 24,
    "grace_multiplier": 1.5,
    "enabled": true,
    "last_sync_at": "2026-02-21T10:00:00Z",
    "created_at": "2026-02-21T08:00:00Z",
    "updated_at": "2026-02-21T08:00:00Z"
  }
]
```

### POST /api/v1/monitors

**Description:** Create a new sync source monitor.

**Request:**
```json
{
  "source_name": "backup-server",
  "expected_interval_hours": 24,
  "grace_multiplier": 1.5,
  "enabled": true
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "source_name": "backup-server",
  "expected_interval_hours": 24,
  "grace_multiplier": 1.5,
  "enabled": true,
  "last_sync_at": null,
  "created_at": "2026-02-21T08:00:00Z",
  "updated_at": "2026-02-21T08:00:00Z"
}
```

**Error Responses:**
- `400` — Invalid input (missing required fields, negative interval)
- `401` — Missing or invalid API key
- `409` — Source name already has a monitor configured

### PUT /api/v1/monitors/{id}

**Description:** Update an existing monitor.

**Request:**
```json
{
  "expected_interval_hours": 48,
  "grace_multiplier": 2.0,
  "enabled": false
}
```

**Response (200):** Updated monitor object.

**Error Responses:**
- `400` — Invalid input
- `401` — Missing or invalid API key
- `404` — Monitor not found

### DELETE /api/v1/monitors/{id}

**Description:** Delete a sync source monitor.

**Response (204):** No content.

**Error Responses:**
- `401` — Missing or invalid API key
- `404` — Monitor not found

### GET /api/v1/failures

**Description:** List failure events with optional filtering.

**Query Parameters:**
- `source_name` (optional) — Filter by source
- `failure_type` (optional) — Filter by "exit_code" or "stale"
- `since` (optional) — ISO datetime, only failures after this time
- `notified` (optional) — Boolean, filter by notification status

**Response (200):**
```json
[
  {
    "id": "uuid",
    "source_name": "backup-server",
    "failure_type": "exit_code",
    "detected_at": "2026-02-21T12:00:00Z",
    "sync_log_id": "uuid",
    "notified": false,
    "details": "Exit code 23",
    "created_at": "2026-02-21T12:00:00Z"
  }
]
```

**Error Responses:**
- `401` — Missing or invalid API key

## 6. UI Behavior

### Dashboard Sync Table (modification)

- **Failed syncs:** Row shows a red "Failed" badge with exit code tooltip
- **Existing syncs without exit_code:** No badge (treated as successful)

### Monitor Configuration Panel

- **Loading:** Spinner while monitors load
- **Empty:** "No sync monitors configured. Add one to track sync frequency."
- **Success:** Table of monitors with source name, interval, grace period, status, and edit/delete actions
- **Error:** Toast notification with error message

### Stale Source Indicator

- **On dashboard:** Sources with stale status show an amber "Stale" warning badge
- **In monitor list:** Last sync time shown with relative time ("37 hours ago — overdue")

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Sync log with exit_code 0 | Treated as successful, no FailureEvent created |
| Sync log with no exit_code field | Treated as successful (backward compatibility) |
| Source with no monitor configured | Not checked for staleness, no stale alerts |
| Monitor with enabled=false | Not checked for staleness |
| Multiple stale checks while source remains stale | Only one FailureEvent per stale window — don't create duplicates until source syncs and goes stale again |
| Scheduler crashes or fails | Log error, retry on next cycle, don't crash the app |
| DB unreachable during stale check | Log warning, skip that check cycle |
| Sync arrives just after stale flag | FailureEvent remains but `last_sync_at` updates; next check will not re-flag |
| Source syncs with non-zero exit code and is also stale | Two separate FailureEvents (one exit_code, one stale) |
| Monitor deleted while FailureEvents exist | FailureEvents are preserved for history; no future stale checks for that source |

## 8. Dependencies

- Existing SyncLog model and POST `/api/v1/sync-logs` endpoint (modification)
- APScheduler or asyncio-based background task for periodic stale checks
- Downstream: Webhook Notification Service (M2) will consume FailureEvents where `notified=false`

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-21 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
