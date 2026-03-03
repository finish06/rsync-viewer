# Spec: Synthetic Monitoring

**Version:** 0.1.0
**Created:** 2026-03-01
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

A built-in background task that periodically performs a synthetic transaction against the application's own API — submitting a canned rsync log via POST, verifying the response, and deleting it on success. If any step fails, a webhook notification is dispatched using the existing webhook system. Prometheus metrics expose check status and latency for Grafana dashboards.

### User Story

As a homelab administrator, I want the application to continuously verify its own health by running synthetic transactions, so that I am immediately notified via Discord/webhook if the ingestion pipeline breaks — without relying on external monitoring tools.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A background task runs on a configurable interval (default 300s) when `SYNTHETIC_CHECK_ENABLED=true` | Must |
| AC-002 | The task POSTs a canned rsync log to `POST /api/v1/sync-logs` using an internal API key, and verifies a 201 response with expected fields (`id`, `source_name`, `status`) | Must |
| AC-003 | On successful POST, the task DELETEs the created sync log by ID via `DELETE /api/v1/sync-logs/{id}` and verifies a 204 response | Must |
| AC-004 | On POST failure (non-201 status, timeout, connection error), the task dispatches a webhook notification with event type `synthetic_failure` to all enabled webhook endpoints | Must |
| AC-005 | On DELETE failure, the task logs a warning but does NOT fire a webhook (orphaned entries with source_name `__synthetic_check` are tolerable) | Must |
| AC-006 | The synthetic log uses source_name `__synthetic_check` (double underscore prefix signals internal use) and a hardcoded canned rsync output with known expected values | Must |
| AC-007 | The task uses the app's own `DEFAULT_API_KEY` (debug key) or a dedicated internal API key for authentication — no external credentials required | Must |
| AC-008 | Prometheus gauge `rsync_synthetic_check_status` (1=passing, 0=failing) and histogram `rsync_synthetic_check_duration_seconds` are recorded on each cycle | Must |
| AC-009 | The `/health` endpoint response includes `synthetic_check: {status, last_check_at, last_latency_ms}` when synthetic monitoring is enabled | Should |
| AC-010 | An admin settings page section "Synthetic Monitoring" shows enable/disable toggle, interval configuration, and last check result with timestamp | Should |
| AC-011 | The task gracefully shuts down when the application stops (same pattern as retention background task) | Must |
| AC-012 | When `SYNTHETIC_CHECK_ENABLED` is false or unset, no background task is started and no resources are consumed | Must |

## 3. User Test Cases

### TC-001: Happy path — synthetic check passes

**Precondition:** App running with `SYNTHETIC_CHECK_ENABLED=true`, at least one webhook endpoint configured
**Steps:**
1. Wait for synthetic check interval to elapse
2. Observe application logs
3. Query `GET /api/v1/sync-logs?source_name=__synthetic_check`
**Expected Result:** Logs show "Synthetic check passed" with latency. No `__synthetic_check` entries remain in the database. No webhook fired. Prometheus metric `rsync_synthetic_check_status` = 1.
**Screenshot Checkpoint:** N/A (backend only)
**Maps to:** TBD

### TC-002: Failure path — database is unreachable

**Precondition:** App running with synthetic checks enabled. Database becomes unavailable after startup.
**Steps:**
1. Stop the database container
2. Wait for next synthetic check cycle
3. Observe application logs and webhook notifications
**Expected Result:** Logs show "Synthetic check FAILED: POST returned 500". Webhook notification dispatched with event type `synthetic_failure` containing error details. Prometheus metric `rsync_synthetic_check_status` = 0.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-003: Settings page — view and toggle synthetic monitoring

**Precondition:** Logged in as admin
**Steps:**
1. Navigate to Settings page
2. Locate "Synthetic Monitoring" section
3. Observe current status (enabled/disabled, last check time, result)
4. Toggle enable/disable
**Expected Result:** Section shows current state. Toggle changes `SYNTHETIC_CHECK_ENABLED` in runtime config. Last check result displays timestamp and pass/fail status.
**Screenshot Checkpoint:** tests/screenshots/synthetic-monitoring/step-03-settings-section.png
**Maps to:** TBD

### TC-004: Health endpoint includes synthetic status

**Precondition:** Synthetic checks enabled, at least one check has completed
**Steps:**
1. `GET /health`
2. Inspect response JSON
**Expected Result:** Response includes `"synthetic_check": {"status": "passing", "last_check_at": "2026-...", "last_latency_ms": 45}`
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

## 4. Data Model

No new database tables. The synthetic check is stateless — it creates and immediately deletes sync log entries. Runtime state (last result, timestamp) is held in memory.

### In-Memory State

| Field | Type | Description |
|-------|------|-------------|
| enabled | bool | Whether synthetic checks are active |
| interval_seconds | int | Seconds between checks (default 300) |
| last_status | str | `"passing"`, `"failing"`, or `"unknown"` |
| last_check_at | datetime or None | Timestamp of most recent check |
| last_latency_ms | float or None | Duration of last check in milliseconds |
| last_error | str or None | Error message from last failure |

### Canned Rsync Log

A hardcoded rsync output string with known parse results:

```
sending incremental file list
synthetic-test-file.txt
              100 100%    0.00kB/s    0:00:00 (xfr#1, to-chk=0/1)

Number of files: 1 (reg: 1)
Number of created files: 0
Number of deleted files: 0
Number of regular files transferred: 1
Total file size: 100 bytes
Total transferred file size: 100 bytes
Literal data: 100 bytes
Matched data: 0 bytes
File list size: 0
Total bytes sent: 150
Total bytes received: 35
sent 150 bytes  received 35 bytes  370.00 bytes/sec
total size is 100  speedup is 0.54
```

Expected parsed values: `file_count=1`, `bytes_sent=150`, `bytes_received=35`, `status="completed"`, `is_dry_run=false`.

## 5. API Contract

### Enhanced GET /health

**Description:** Existing health endpoint extended with synthetic check status.

**Response (200):**
```json
{
  "status": "ok",
  "synthetic_check": {
    "status": "passing",
    "last_check_at": "2026-03-01T20:00:00Z",
    "last_latency_ms": 42.5
  }
}
```

When synthetic checks are disabled:
```json
{
  "status": "ok",
  "synthetic_check": null
}
```

### Webhook Payload (event type: synthetic_failure)

Dispatched to all enabled webhook endpoints using the existing `dispatch_webhooks` flow. The synthetic check creates a transient `FailureEvent` with `failure_type="synthetic_failure"`.

```json
{
  "event_type": "synthetic_failure",
  "source_name": "__synthetic_check",
  "failure_type": "synthetic_failure",
  "details": "POST /api/v1/sync-logs returned 500: Internal Server Error",
  "detected_at": "2026-03-01T20:05:00Z"
}
```

## 6. UI Behavior

### Settings Page — Synthetic Monitoring Section

Located in the admin Settings page as an HTMX partial, alongside SMTP and OIDC sections.

**States:**
- **Disabled:** Toggle is off. Shows "Synthetic monitoring is disabled."
- **Enabled, no data yet:** Toggle is on. Shows "Waiting for first check..." with configured interval.
- **Enabled, passing:** Toggle is on. Green status badge. Shows last check timestamp and latency.
- **Enabled, failing:** Toggle is on. Red status badge. Shows last check timestamp and error message.

### Screenshot Checkpoints

| Step | Description | Path |
|------|-------------|------|
| 1 | Settings page with synthetic monitoring section visible | tests/screenshots/synthetic-monitoring/step-01-settings.png |
| 2 | Enabled state showing passing status | tests/screenshots/synthetic-monitoring/step-02-passing.png |
| 3 | Enabled state showing failing status | tests/screenshots/synthetic-monitoring/step-03-failing.png |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| POST succeeds but DELETE returns 404 | Log warning. No webhook. Entry may have been already cleaned up. |
| POST succeeds but DELETE returns 403 | Log warning. Indicates API key lacks admin role — log actionable error message. |
| POST times out (>10s) | Treat as failure. Fire webhook with timeout details. |
| Webhook dispatch itself fails | Existing webhook retry logic handles this (3 attempts with backoff). |
| App starts with DB down | Synthetic check fires on first interval, detects failure, sends webhook (if webhook endpoint is external). |
| Multiple app instances running | Each instance runs its own synthetic check independently. Duplicate `__synthetic_check` entries may briefly exist — acceptable since they're deleted immediately. |
| Interval set to very low value (<30s) | Minimum enforced at 30 seconds to avoid self-DoS. |
| `__synthetic_check` logs visible in dashboard | The source_name uses `__` prefix. Dashboard queries should exclude it (or filter is added to default query). |

## 8. Dependencies

- Existing webhook dispatch system (`app/services/webhook_dispatcher.py`)
- Existing Prometheus metrics infrastructure (`app/metrics.py`)
- Existing retention background task pattern (`app/services/retention.py`, `app/main.py` lifespan)
- Existing settings page HTMX partial pattern (`app/routes/settings.py`)
- `httpx` for internal HTTP calls (already a dependency via test suite)
- Alembic migrations (for any future schema changes, though none needed here)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-01 | 0.1.0 | finish06 + Claude | Initial spec from /add:spec interview |
