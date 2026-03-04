# Spec: Synthetic Monitoring

**Version:** 0.2.0
**Created:** 2026-03-01
**PRD Reference:** docs/prd.md
**Status:** Implementing

## 1. Overview

A built-in background task that periodically performs a synthetic transaction against the application's own API — submitting a canned rsync log via POST, verifying the response, and deleting it on success. If any step fails, a webhook notification is dispatched using the existing webhook system. Prometheus metrics expose check status and latency for Grafana dashboards.

**v0.2.0 additions:** The synthetic monitoring toggle in the UI must actually start/stop the background task at runtime (no restart required). Configuration is persisted to the database so it survives restarts. A monitoring status dashboard shows check history with pass/fail timeline and uptime percentage.

### User Story

As a homelab administrator, I want the application to continuously verify its own health by running synthetic transactions, so that I am immediately notified via Discord/webhook if the ingestion pipeline breaks — without relying on external monitoring tools.

As a homelab administrator, I want to enable/disable synthetic monitoring from the UI without restarting the app, and see a history of check results, so that I can monitor health trends and verify the feature is working.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A background task runs on a configurable interval (default 300s) when synthetic monitoring is enabled | Must |
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
| AC-012 | When synthetic monitoring is disabled, no background task is running and no resources are consumed | Must |
| AC-013 | Toggling the enable/disable switch in the Settings UI immediately starts or stops the background task without requiring an app restart | Must |
| AC-014 | Synthetic monitoring configuration (enabled, interval, API key) is persisted to the database so it survives app restarts | Must |
| AC-015 | On app startup, the app reads persisted synthetic config from the DB. If enabled, the background task starts automatically. The `SYNTHETIC_CHECK_ENABLED` env var serves as a bootstrap default only (first run before DB config exists) | Must |
| AC-016 | Check results (timestamp, status, latency_ms, error) are stored in a database table (last 100 results, auto-pruned) | Must |
| AC-017 | The Settings UI displays a check history section showing the last 24 hours of results as a pass/fail timeline with uptime percentage | Must |
| AC-018 | The check history auto-refreshes via HTMX polling (every 60 seconds) so the admin can watch checks in near-real-time | Should |

## 3. User Test Cases

### TC-001: Happy path — synthetic check passes

**Precondition:** App running with synthetic monitoring enabled, at least one webhook endpoint configured
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

### TC-003: Enable synthetic monitoring from UI without restart

**Precondition:** Logged in as admin, synthetic monitoring currently disabled
**Steps:**
1. Navigate to Settings > Monitoring tab
2. Check the "Enable synthetic monitoring" checkbox
3. Set interval to 60 seconds
4. Click Save
5. Wait 60-90 seconds
6. Observe the check history section
**Expected Result:** Save confirms "Synthetic monitoring enabled." The background task starts immediately. After ~60s, the first check result appears in the history timeline showing "Passing" with latency. No app restart was needed.
**Screenshot Checkpoint:** tests/screenshots/synthetic-monitoring/step-03-enabled-from-ui.png
**Maps to:** TBD

### TC-004: Disable synthetic monitoring from UI without restart

**Precondition:** Logged in as admin, synthetic monitoring currently enabled and running
**Steps:**
1. Navigate to Settings > Monitoring tab
2. Uncheck the "Enable synthetic monitoring" checkbox
3. Click Save
4. Wait for what would be the next check interval
**Expected Result:** Save confirms "Synthetic monitoring disabled." The background task stops. No new checks appear. `/health` shows `synthetic_check: null`.
**Screenshot Checkpoint:** tests/screenshots/synthetic-monitoring/step-04-disabled-from-ui.png
**Maps to:** TBD

### TC-005: Configuration survives app restart

**Precondition:** Synthetic monitoring enabled from the UI, checks running
**Steps:**
1. Restart the app container (`docker-compose restart app`)
2. Navigate to Settings > Monitoring tab
3. Observe the enable toggle and interval
**Expected Result:** Toggle is still checked. Interval matches what was set before restart. Background task is running. New check results appear in history.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-006: Check history shows pass/fail timeline

**Precondition:** Synthetic monitoring has been running for at least 30 minutes
**Steps:**
1. Navigate to Settings > Monitoring tab
2. Look at the check history section
**Expected Result:** Shows a timeline of recent checks with green (pass) and red (fail) indicators. Displays uptime percentage (e.g., "100% — 12/12 checks passed in last 24h"). Most recent check is shown first with timestamp and latency.
**Screenshot Checkpoint:** tests/screenshots/synthetic-monitoring/step-06-check-history.png
**Maps to:** TBD

### TC-007: Health endpoint includes synthetic status

**Precondition:** Synthetic checks enabled, at least one check has completed
**Steps:**
1. `GET /health`
2. Inspect response JSON
**Expected Result:** Response includes `"synthetic_check": {"status": "passing", "last_check_at": "2026-...", "last_latency_ms": 45}`
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

## 4. Data Model

### SyntheticCheckConfig (database table — new)

Singleton settings row persisted to DB. Replaces env-var-only configuration.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | Yes | Primary key (always 1 — singleton) |
| enabled | bool | Yes | Whether synthetic checks are active (default false) |
| interval_seconds | int | Yes | Seconds between checks (default 300, min 30) |
| api_key | str | No | Dedicated API key override; falls back to DEFAULT_API_KEY if empty |
| updated_at | datetime | Yes | Last time config was changed |

### SyntheticCheckResult (database table — new)

Stores recent check results for the history timeline.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | Yes | Auto-increment primary key |
| checked_at | datetime | Yes | When the check ran (indexed) |
| status | str | Yes | `"passing"` or `"failing"` |
| latency_ms | float | Yes | Check duration in milliseconds |
| error | str | No | Error message if failing, null if passing |

Auto-pruned: keep only the most recent 100 rows. Prune after each insert.

### In-Memory State (unchanged)

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

### GET /htmx/synthetic-history

**Description:** HTMX partial returning the check history timeline for the last 24 hours.

**Response (200):** HTML partial with pass/fail timeline, uptime percentage, and recent check list.

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

Located in the admin Settings > Monitoring tab, alongside rsync client setup.

**States:**
- **Disabled:** Toggle is off. Shows "Synthetic monitoring is disabled." No history section.
- **Enabled, no data yet:** Toggle is on. Shows "Waiting for first check..." with configured interval. Empty history.
- **Enabled, passing:** Toggle is on. Green status badge. Shows last check timestamp and latency. History timeline shows green dots.
- **Enabled, failing:** Toggle is on. Red status badge. Shows last check timestamp and error message. History timeline shows red dots for failures.

**Enable/Disable behavior:**
- Toggling ON + Save immediately starts the background task and persists config to DB
- Toggling OFF + Save immediately cancels the background task and persists config to DB
- No "requires restart" message — the change is live
- Success message confirms the action: "Synthetic monitoring enabled." / "Synthetic monitoring disabled."

### Check History Section

Below the config form, visible when monitoring is enabled:

- **Uptime bar:** Horizontal bar showing last 24h of checks as colored segments (green=pass, red=fail, gray=no data)
- **Uptime percentage:** "100% — 48/48 checks passed in last 24h"
- **Recent checks list:** Last 10 checks in a compact table (time, status badge, latency)
- **Auto-refresh:** HTMX polls `GET /htmx/synthetic-history` every 60s to update without full page reload

### Screenshot Checkpoints

| Step | Description | Path |
|------|-------------|------|
| 1 | Settings page with synthetic monitoring section visible | tests/screenshots/synthetic-monitoring/step-01-settings.png |
| 2 | Enabled state showing passing status with history | tests/screenshots/synthetic-monitoring/step-02-passing.png |
| 3 | Enabled state showing failing status with history | tests/screenshots/synthetic-monitoring/step-03-failing.png |
| 4 | Check history timeline with mixed pass/fail | tests/screenshots/synthetic-monitoring/step-04-history.png |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| POST succeeds but DELETE returns 404 | Log warning. No webhook. Entry may have been already cleaned up. |
| POST succeeds but DELETE returns 403 | Log warning. Indicates API key lacks admin role — log actionable error message. |
| POST times out (>10s) | Treat as failure. Fire webhook with timeout details. |
| Webhook dispatch itself fails | Existing webhook retry logic handles this (3 attempts with backoff). |
| App starts with DB down | Cannot read config from DB. Fall back to env var `SYNTHETIC_CHECK_ENABLED`. Log warning about DB unavailability. |
| Multiple app instances running | Each instance runs its own synthetic check independently. Duplicate `__synthetic_check` entries may briefly exist — acceptable since they're deleted immediately. |
| Interval set to very low value (<30s) | Minimum enforced at 30 seconds to avoid self-DoS. |
| `__synthetic_check` logs visible in dashboard | The source_name uses `__` prefix. Dashboard queries should exclude it (or filter is added to default query). |
| DB config table doesn't exist yet (first run / migration) | Fall back to env vars. Run Alembic migration to create table. |
| Enable toggled rapidly (on/off/on) | Each toggle cancels previous task before starting new one. No duplicate tasks. |
| Check history table exceeds 100 rows | Auto-prune oldest rows after each insert (DELETE WHERE id NOT IN top 100). |
| App restarts while checks were enabled via UI | On startup, read `SyntheticCheckConfig` from DB. If enabled=true, start the background task. Env var is ignored if DB config exists. |

## 8. Dependencies

- Existing webhook dispatch system (`app/services/webhook_dispatcher.py`)
- Existing Prometheus metrics infrastructure (`app/metrics.py`)
- Existing retention background task pattern (`app/services/retention.py`, `app/main.py` lifespan)
- Existing settings page HTMX partial pattern (`app/routes/settings.py`)
- `httpx` for internal HTTP calls (already a dependency via test suite)
- Alembic migrations (new migration for `SyntheticCheckConfig` and `SyntheticCheckResult` tables)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-01 | 0.1.0 | finish06 + Claude | Initial spec from /add:spec interview |
| 2026-03-04 | 0.2.0 | finish06 + Claude | AC-013–AC-018: runtime enable/disable without restart, DB-persisted config, check history with reporting UI |
