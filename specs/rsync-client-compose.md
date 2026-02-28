# Spec: Rsync Client Docker Compose

**Version:** 0.1.0
**Created:** 2026-02-28
**PRD Reference:** docs/prd.md
**Status:** Approved

## 1. Overview

Provide ready-to-use Docker Compose examples that run rsync on a cron schedule inside a lightweight container. Users mount their local sync directory, configure the remote host and Rsync Viewer URL via environment variables, and the container handles scheduling, executing rsync, capturing output, and shipping logs to the Rsync Viewer API automatically.

The deliverable lives in `examples/rsync-client/` within this repository and includes a custom Alpine-based Dockerfile, separate compose files for pull and push modes, an entrypoint script that wires up cron + rsync + log submission, and documentation.

### User Story

As a homelab administrator, I want a drop-in docker-compose file that runs rsync on a schedule and automatically sends logs to my Rsync Viewer instance, so that I can monitor all my backup jobs from the dashboard without writing custom scripts.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A custom Dockerfile based on Alpine produces a lightweight image (<30MB) containing rsync, openssh-client, curl, and dcron/busybox-cron | Must |
| AC-002 | A `docker-compose.pull.yml` example pulls files FROM a remote server into a mounted local directory on a cron schedule | Must |
| AC-003 | A `docker-compose.push.yml` example pushes files FROM a mounted local directory TO a remote server on a cron schedule | Must |
| AC-004 | An entrypoint script dynamically generates the crontab from the `CRON_SCHEDULE` environment variable | Must |
| AC-005 | After each rsync run, the script captures stdout/stderr and POSTs the raw output to `${RSYNC_VIEWER_URL}/api/v1/sync-logs` with the configured API key | Must |
| AC-006 | The API payload includes `source_name`, `start_time`, `end_time`, and `raw_content` matching the existing `SyncLogCreate` schema | Must |
| AC-007 | SSH authentication works by mounting the host's SSH key file into the container (default: `~/.ssh/id_rsa`) | Must |
| AC-008 | A `.env.example` file documents all configurable environment variables with sensible defaults | Must |
| AC-009 | The `RSYNC_ARGS` environment variable allows users to pass additional rsync flags (default: `-avz --stats`) | Must |
| AC-010 | The `SSH_PORT` environment variable allows connecting to non-standard SSH ports (default: `22`) | Should |
| AC-011 | The container logs each rsync invocation with timestamps to stdout for `docker logs` visibility | Should |
| AC-012 | A `README.md` in `examples/rsync-client/` explains setup, configuration, and both pull/push usage | Must |
| AC-013 | The rsync script handles the case where the Rsync Viewer API is unreachable (log warning, don't crash, retry next cycle) | Must |
| AC-014 | The container runs as a non-root user where possible for security | Should |

## 3. User Test Cases

### TC-001: Pull Mode — Scheduled Sync from Remote to Local

**Precondition:** User has a remote server with SSH access, a running Rsync Viewer instance, and an API key.
**Steps:**
1. Copy `.env.example` to `.env` and fill in `REMOTE_HOST`, `REMOTE_USER`, `REMOTE_PATH`, `RSYNC_VIEWER_URL`, `RSYNC_VIEWER_API_KEY`, `RSYNC_SOURCE_NAME`, and `CRON_SCHEDULE`
2. Mount SSH key and local data directory in `docker-compose.pull.yml`
3. Run `docker compose -f docker-compose.pull.yml up -d`
4. Wait for the cron schedule to trigger (or exec into container and run the sync script manually)
5. Open Rsync Viewer dashboard
**Expected Result:** A new sync log entry appears in the dashboard for the configured `RSYNC_SOURCE_NAME` with parsed transfer statistics.
**Screenshot Checkpoint:** N/A (no UI changes to this project)
**Maps to:** TBD

### TC-002: Push Mode — Scheduled Sync from Local to Remote

**Precondition:** User has a remote server with SSH access, a running Rsync Viewer instance, and an API key.
**Steps:**
1. Copy `.env.example` to `.env` and fill in variables; set `REMOTE_PATH` as the destination
2. Mount SSH key and local source directory in `docker-compose.push.yml`
3. Run `docker compose -f docker-compose.push.yml up -d`
4. Wait for cron trigger or manually invoke the sync script
5. Check Rsync Viewer dashboard
**Expected Result:** A new sync log entry appears with the push operation's transfer statistics.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-003: API Unreachable — Graceful Failure

**Precondition:** Rsync client container is running. Rsync Viewer is stopped or unreachable.
**Steps:**
1. Stop the Rsync Viewer instance
2. Trigger or wait for a scheduled rsync run
3. Check container logs via `docker logs`
**Expected Result:** Rsync completes normally. Container logs show a warning that the API submission failed. Container continues running and will retry on the next scheduled sync.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-004: Custom Rsync Arguments

**Precondition:** Container is configured and running.
**Steps:**
1. Set `RSYNC_ARGS=-avz --stats --delete --exclude='.DS_Store'` in `.env`
2. Restart the container
3. Trigger a sync
**Expected Result:** Rsync runs with the custom arguments. The raw output (including delete operations) is captured and sent to the API.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-005: Non-Standard SSH Port

**Precondition:** Remote server runs SSH on port 2222.
**Steps:**
1. Set `SSH_PORT=2222` in `.env`
2. Start the container
3. Trigger a sync
**Expected Result:** Rsync connects via SSH on port 2222 and completes successfully.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

## 4. Data Model

No new database models — this feature produces files only (Dockerfile, compose files, scripts). It uses the existing `SyncLogCreate` API schema for log submission.

### SyncLogCreate (existing — referenced by client script)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source_name | string | Yes | Identifier for the sync source |
| start_time | datetime (ISO 8601) | Yes | When the rsync operation started |
| end_time | datetime (ISO 8601) | Yes | When the rsync operation completed |
| raw_content | string | Yes | Raw rsync command output |

## 5. API Contract

No new API endpoints. The client script POSTs to the existing endpoint:

### POST /api/v1/sync-logs

**Description:** Submit rsync output for parsing and storage (existing endpoint).

**Request Headers:**
```
X-API-Key: {RSYNC_VIEWER_API_KEY}
Content-Type: application/json
```

**Request Body:**
```json
{
  "source_name": "media-backup",
  "start_time": "2026-02-28T10:00:00Z",
  "end_time": "2026-02-28T10:05:30Z",
  "raw_content": "receiving file list ... done\n..."
}
```

**Response (201):** Log created successfully.
**Error Responses:**
- `401` — Invalid or missing API key
- `413` — Raw content exceeds size limit

## 6. UI Behavior

N/A — this feature is a client-side Docker artifact, not a UI change. Logs appear in the existing dashboard automatically.

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Rsync Viewer API is unreachable | Log warning to stdout, continue running, retry next cycle |
| SSH key not mounted or invalid | Rsync fails with SSH error; error output is captured and sent to API (shows as failed sync) |
| Empty rsync output (no files changed) | Still submit to API — the parser handles empty syncs |
| Very large rsync output (>10MB) | Truncate raw_content to 10MB before submission (API limit) |
| Invalid cron expression | Container logs error at startup and exits with non-zero code |
| Missing required env vars | Entrypoint validates required vars and exits with clear error message |
| Remote host key not in known_hosts | Use `StrictHostKeyChecking=accept-new` for first connection (homelab-appropriate) |
| Concurrent cron triggers (long-running sync overlaps next schedule) | Use flock or a PID file to prevent overlapping rsync runs |

## 8. Dependencies

- Existing `POST /api/v1/sync-logs` API endpoint (already implemented)
- Existing `SyncLogCreate` schema (already implemented)
- Alpine Linux base image (public Docker Hub)
- No new Python dependencies in the main application

## 9. File Deliverables

```
examples/rsync-client/
├── Dockerfile              # Alpine + rsync + openssh-client + curl + cron
├── docker-compose.pull.yml # Pull mode example
├── docker-compose.push.yml # Push mode example
├── .env.example            # All configurable environment variables
├── entrypoint.sh           # Container entrypoint: validates env, sets up cron
├── sync.sh                 # The rsync + log submission script run by cron
└── README.md               # Setup and usage documentation
```

## 10. Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RSYNC_VIEWER_URL` | Yes | — | Base URL of the Rsync Viewer instance |
| `RSYNC_VIEWER_API_KEY` | Yes | — | API key for authentication |
| `RSYNC_SOURCE_NAME` | Yes | — | Name shown in the dashboard |
| `REMOTE_HOST` | Yes | — | Remote SSH hostname or IP |
| `REMOTE_USER` | Yes | — | SSH username |
| `REMOTE_PATH` | Yes | — | Path on the remote server |
| `CRON_SCHEDULE` | No | `0 */6 * * *` | Cron expression for sync frequency |
| `RSYNC_ARGS` | No | `-avz --stats` | Additional rsync flags |
| `SSH_PORT` | No | `22` | SSH port on the remote server |

## 11. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-28 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
