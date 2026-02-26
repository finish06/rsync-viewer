# Spec: Sync Scheduling

**Version:** 0.1.0
**Created:** 2026-02-22
**PRD Reference:** docs/prd.md
**Status:** Draft
**Milestone:** M10 — Sync Management

## 1. Overview

Enable users to trigger and schedule rsync operations directly from the web UI, transforming rsync-viewer from a passive log viewer into an active sync management platform. Includes on-demand sync triggering, cron-based scheduling, real-time progress tracking, and automatic retry on failure.

### User Story

As a homelab administrator, I want to trigger rsync jobs from the web UI and set up recurring schedules, so that I can manage all my backup operations from a single dashboard instead of managing cron jobs on individual machines.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A "Run Now" button on the dashboard triggers an rsync sync for a configured source | Must |
| AC-002 | Sync configurations (source, destination, rsync flags, SSH key path) are stored in the database | Must |
| AC-003 | Users can create, edit, and delete sync configurations via the UI | Must |
| AC-004 | Cron-style schedules can be attached to sync configurations with enable/disable toggle | Must |
| AC-005 | Scheduled syncs execute automatically at the configured times | Must |
| AC-006 | Real-time sync progress is displayed via WebSocket or SSE updates | Should |
| AC-007 | Running syncs can be cancelled from the UI | Should |
| AC-008 | Failed syncs automatically retry with configurable count and exponential backoff | Should |
| AC-009 | A "currently running syncs" view shows active sync operations | Must |
| AC-010 | Sync output is captured and stored as a regular sync log entry upon completion | Must |
| AC-011 | Next scheduled run time is displayed for each configured schedule | Must |
| AC-012 | Dry-run mode is available for on-demand syncs | Should |

## 3. User Test Cases

### TC-001: Trigger on-demand sync

**Precondition:** At least one sync configuration exists
**Steps:**
1. Navigate to the sync configurations page
2. Click "Run Now" on a configured source
3. Observe the sync progress
4. Wait for completion
**Expected Result:** Sync starts immediately, progress updates appear in real time, completed sync log appears in history with full parsed statistics.
**Screenshot Checkpoint:** tests/screenshots/sync-scheduling/step-01-run-now.png
**Maps to:** AC-001, AC-006, AC-010

### TC-002: Create sync configuration

**Precondition:** App running
**Steps:**
1. Navigate to sync configuration management
2. Click "Add Configuration"
3. Fill in: name "NAS Backup", source "/data/", destination "user@nas:/backup/", rsync flags "-avz --delete", SSH key path "/home/user/.ssh/id_rsa"
4. Save the configuration
**Expected Result:** Configuration is saved and appears in the list. Fields are validated (source/destination required, SSH key path exists or is empty).
**Screenshot Checkpoint:** tests/screenshots/sync-scheduling/step-02-add-config.png
**Maps to:** AC-002, AC-003

### TC-003: Schedule a recurring sync

**Precondition:** A sync configuration exists
**Steps:**
1. Edit a sync configuration
2. Add a schedule: "Every day at 2:00 AM" (cron: `0 2 * * *`)
3. Enable the schedule
4. Save and verify next run time is displayed
**Expected Result:** Schedule is saved. Next run time is calculated and displayed. When the scheduled time arrives, the sync executes automatically.
**Screenshot Checkpoint:** tests/screenshots/sync-scheduling/step-03-add-schedule.png
**Maps to:** AC-004, AC-005, AC-011

### TC-004: Automatic retry on failure

**Precondition:** A sync configuration with retry enabled (max 3 retries)
**Steps:**
1. Trigger a sync that will fail (e.g., unreachable destination)
2. Observe retry behavior
**Expected Result:** First attempt fails. Up to 3 retries occur with increasing delay (30s, 60s, 120s). Each attempt is logged. If all retries fail, sync is marked as failed and failure detection triggers.
**Screenshot Checkpoint:** N/A (backend)
**Maps to:** AC-008

### TC-005: Cancel running sync

**Precondition:** A sync is currently running
**Steps:**
1. Navigate to "Currently Running" view
2. Click "Cancel" on the running sync
3. Confirm cancellation
**Expected Result:** Rsync process is terminated. Sync log entry is created with cancelled status. UI updates to show sync is no longer running.
**Screenshot Checkpoint:** tests/screenshots/sync-scheduling/step-05-cancel-sync.png
**Maps to:** AC-007, AC-009

## 4. Data Model

### SyncConfiguration (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| name | String(100) | Yes | Human-readable name |
| source_path | String(1024) | Yes | Rsync source path (local or remote) |
| destination_path | String(1024) | Yes | Rsync destination path (local or remote) |
| rsync_flags | String(512) | No | Additional rsync command flags (default: "-avz") |
| ssh_key_path | String(512) | No | Path to SSH private key for remote syncs |
| exclude_patterns | JSON | No | Array of rsync --exclude patterns |
| enabled | Boolean | Yes | Whether this configuration is active. Default true |
| max_retries | Integer | Yes | Retry count on failure (default: 0) |
| created_at | DateTime | Yes | Record creation timestamp |
| updated_at | DateTime | Yes | Last modification timestamp |

### SyncSchedule (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| sync_config_id | UUID (FK) | Yes | Reference to SyncConfiguration |
| cron_expression | String(100) | Yes | Cron schedule expression (e.g., "0 2 * * *") |
| enabled | Boolean | Yes | Whether this schedule is active. Default true |
| last_run_at | DateTime | No | When this schedule last executed |
| next_run_at | DateTime | No | Calculated next execution time |
| created_at | DateTime | Yes | Record creation timestamp |

### SyncExecution (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| sync_config_id | UUID (FK) | Yes | Reference to SyncConfiguration |
| schedule_id | UUID (FK) | No | Reference to SyncSchedule (null for on-demand) |
| status | String(20) | Yes | "pending", "running", "completed", "failed", "cancelled" |
| pid | Integer | No | OS process ID of running rsync (for cancellation) |
| attempt_number | Integer | Yes | Current attempt (1-based) |
| started_at | DateTime | No | When execution began |
| completed_at | DateTime | No | When execution finished |
| sync_log_id | UUID (FK) | No | Reference to created SyncLog entry (after completion) |
| error_message | String | No | Error details if failed |

### Relationships

- `SyncSchedule.sync_config_id` -> `SyncConfiguration.id` (FK, cascade delete)
- `SyncExecution.sync_config_id` -> `SyncConfiguration.id` (FK)
- `SyncExecution.schedule_id` -> `SyncSchedule.id` (FK, nullable)
- `SyncExecution.sync_log_id` -> `SyncLog.id` (FK, nullable)
- One SyncConfiguration can have many SyncSchedules
- One SyncConfiguration can have many SyncExecutions

## 5. API Contract

### GET /api/v1/sync-configs

**Description:** List all sync configurations.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "NAS Backup",
    "source_path": "/data/",
    "destination_path": "user@nas:/backup/",
    "rsync_flags": "-avz --delete",
    "ssh_key_path": "/home/user/.ssh/id_rsa",
    "exclude_patterns": ["*.tmp", ".cache/"],
    "enabled": true,
    "max_retries": 3,
    "schedules": [
      {
        "id": "uuid",
        "cron_expression": "0 2 * * *",
        "enabled": true,
        "next_run_at": "2026-02-23T02:00:00Z"
      }
    ]
  }
]
```

### POST /api/v1/sync-configs

**Description:** Create a new sync configuration.

**Request:**
```json
{
  "name": "NAS Backup",
  "source_path": "/data/",
  "destination_path": "user@nas:/backup/",
  "rsync_flags": "-avz --delete",
  "ssh_key_path": "/home/user/.ssh/id_rsa",
  "exclude_patterns": ["*.tmp"],
  "max_retries": 3
}
```

**Response (201):** Created configuration object.

### POST /api/v1/sync-configs/{id}/run

**Description:** Trigger an on-demand sync execution.

**Request:**
```json
{
  "dry_run": false
}
```

**Response (202):**
```json
{
  "execution_id": "uuid",
  "status": "pending",
  "message": "Sync queued for execution"
}
```

### DELETE /api/v1/sync-executions/{id}

**Description:** Cancel a running sync execution.

**Response (200):**
```json
{
  "status": "cancelled",
  "message": "Sync execution cancelled"
}
```

### GET /api/v1/sync-executions

**Description:** List sync executions (running and recent).

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| status | String | No | Filter by status |
| config_id | UUID | No | Filter by sync configuration |

**Response (200):**
```json
[
  {
    "id": "uuid",
    "sync_config_name": "NAS Backup",
    "status": "running",
    "attempt_number": 1,
    "started_at": "2026-02-22T14:00:00Z",
    "completed_at": null
  }
]
```

## 6. UI Behavior

### Sync Configuration Page

- **Location:** `/sync-configs` (new page, linked from nav)
- **List view:** Table of configurations with name, source, destination, schedule status, last run, next run, "Run Now" button
- **Add/Edit form:** Fields for all configuration properties, cron expression builder with presets (hourly, daily, weekly)
- **Delete:** Confirmation dialog warning about schedule removal

### Running Syncs Dashboard

- **Location:** Section on main dashboard or `/sync-executions`
- **Active syncs:** Card per running sync showing name, progress (if available), elapsed time, cancel button
- **Updates:** WebSocket or SSE for real-time status changes
- **Empty:** "No syncs currently running"

### Cron Expression Builder

- **Presets:** "Every hour", "Daily at midnight", "Weekly on Sunday", "Custom"
- **Custom:** Human-readable cron editor with field explanations
- **Validation:** Invalid expressions show error before save
- **Preview:** "Next 5 run times" displayed after entering expression

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Sync triggered while another is running for same config | Queue the new execution, don't run concurrently for same config |
| App restarts during running sync | Detect orphaned executions on startup, mark as "interrupted" |
| SSH key file doesn't exist | Validate at config save time, warn user |
| Destination unreachable | Sync fails, retry mechanism kicks in, failure event created |
| Cron expression results in overlapping runs | Skip if previous run still active, log skip event |
| Very long-running sync (hours) | No timeout by default, status tracked, cancellable |
| Sync produces no output | Create sync log with zero stats, mark as success if exit code 0 |
| Multiple schedules for same config | Each schedule triggers independently |
| Config deleted while sync running | Allow running sync to complete, don't schedule new ones |

## 8. Security Considerations

- **Command injection:** Rsync arguments must be strictly validated — no shell expansion, no semicolons, no pipe operators
- **SSH key access:** Application needs read access to SSH keys — document required permissions
- **Path traversal:** Source/destination paths validated against allowed base directories
- **Process management:** Sync processes run as the application user with no privilege escalation

## 9. Dependencies

- APScheduler or Celery for schedule execution
- asyncio subprocess management for rsync process control
- WebSocket support (or SSE) for real-time updates
- Existing SyncLog model (sync output stored as regular log entry)
- Failure detection spec (failed syncs trigger failure events)
- Error handling spec (for consistent error responses)

## 10. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-22 | 0.1.0 | finish06 | Initial spec from TODO conversion |
