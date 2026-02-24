# Database Schema

All tables use UUID primary keys and UTC timestamps. The ORM layer is SQLModel (SQLAlchemy + Pydantic).

## Tables

### `sync_logs`

Stores parsed rsync synchronization log entries.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Unique identifier |
| `source_name` | VARCHAR(100) | NOT NULL, indexed | Name of the sync source |
| `start_time` | TIMESTAMP | NOT NULL, indexed | When the sync started |
| `end_time` | TIMESTAMP | NOT NULL | When the sync ended |
| `raw_content` | TEXT | NOT NULL | Raw rsync output |
| `total_size_bytes` | BIGINT | nullable | Total size reported by rsync |
| `bytes_sent` | BIGINT | nullable | Bytes sent |
| `bytes_received` | BIGINT | nullable | Bytes received |
| `transfer_speed` | FLOAT | nullable | Transfer speed (bytes/sec) |
| `speedup_ratio` | FLOAT | nullable | rsync speedup ratio |
| `file_count` | INTEGER | nullable | Number of files transferred |
| `file_list` | JSONB | nullable | List of transferred file paths |
| `exit_code` | INTEGER | nullable | rsync exit code |
| `status` | VARCHAR(20) | default "completed" | Sync status |
| `is_dry_run` | BOOLEAN | default false, indexed | Whether this was a dry run |
| `created_at` | TIMESTAMP | default now() | Record creation time |

**Indexes:**
- `ix_sync_logs_source_name` — source_name
- `ix_sync_logs_start_time` — start_time
- `ix_sync_logs_source_name_created_at` — (source_name, created_at) composite
- `ix_sync_logs_exit_code` — exit_code
- `ix_sync_logs_created_at` — created_at
- `ix_sync_logs_is_dry_run` — is_dry_run

### `failure_events`

Tracks detected failure events (non-zero exit codes or stale sources).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Unique identifier |
| `source_name` | VARCHAR(100) | NOT NULL, indexed | Sync source that failed |
| `failure_type` | VARCHAR(20) | NOT NULL, indexed | "exit_code" or "stale" |
| `detected_at` | TIMESTAMP | default now(), indexed | When the failure was detected |
| `sync_log_id` | UUID | FK → sync_logs.id, nullable | Associated sync log (if exit_code failure) |
| `notified` | BOOLEAN | default false | Whether notifications were sent |
| `details` | TEXT | nullable | Additional failure details |
| `created_at` | TIMESTAMP | default now() | Record creation time |

**Indexes:**
- `ix_failure_events_source_name` — source_name
- `ix_failure_events_failure_type` — failure_type
- `ix_failure_events_detected_at` — detected_at
- `ix_failure_events_source_name_detected_at` — (source_name, detected_at) composite

**Foreign Keys:**
- `sync_log_id` references `sync_logs.id`

### `sync_source_monitors`

Configuration for monitoring sync sources and detecting staleness.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Unique identifier |
| `source_name` | VARCHAR(100) | UNIQUE, indexed | Monitored source name |
| `expected_interval_hours` | INTEGER | NOT NULL | Expected sync frequency |
| `grace_multiplier` | FLOAT | default 1.5 | Grace period multiplier |
| `enabled` | BOOLEAN | default true | Whether monitoring is active |
| `last_sync_at` | TIMESTAMP | nullable | Last known sync time |
| `created_at` | TIMESTAMP | default now() | Record creation time |
| `updated_at` | TIMESTAMP | default now() | Last update time |

### `webhook_endpoints`

Webhook endpoint configuration for failure notifications.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Unique identifier |
| `name` | VARCHAR(100) | NOT NULL | Display name |
| `url` | VARCHAR(2048) | NOT NULL | Webhook URL |
| `headers` | JSONB | nullable | Custom HTTP headers |
| `webhook_type` | VARCHAR(20) | default "generic" | "generic" or "discord" |
| `source_filters` | JSONB | nullable | List of source names to filter |
| `enabled` | BOOLEAN | default true, indexed | Whether the webhook is active |
| `consecutive_failures` | INTEGER | default 0 | Consecutive delivery failures |
| `created_at` | TIMESTAMP | default now() | Record creation time |
| `updated_at` | TIMESTAMP | default now() | Last update time |

### `notification_logs`

Audit log of webhook notification delivery attempts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Unique identifier |
| `failure_event_id` | UUID | FK → failure_events.id, indexed | Associated failure event |
| `webhook_endpoint_id` | UUID | FK → webhook_endpoints.id, indexed | Target webhook |
| `status` | VARCHAR(20) | NOT NULL | "success", "failed", or "skipped" |
| `http_status_code` | INTEGER | nullable | HTTP response status code |
| `error_message` | TEXT | nullable | Error details on failure |
| `attempt_number` | INTEGER | default 1 | Retry attempt number |
| `created_at` | TIMESTAMP | default now() | Record creation time |

**Indexes:**
- `ix_notification_logs_failure_event_id` — failure_event_id
- `ix_notification_logs_webhook_endpoint_id` — webhook_endpoint_id
- `ix_notification_logs_created_at` — created_at

**Foreign Keys:**
- `failure_event_id` references `failure_events.id`
- `webhook_endpoint_id` references `webhook_endpoints.id`

### `api_keys`

API key storage for authentication.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Unique identifier |
| `key_hash` | VARCHAR(128) | UNIQUE | Bcrypt hash of the API key |
| `key_prefix` | VARCHAR(12) | default "" | First characters for identification |
| `name` | VARCHAR(100) | NOT NULL | Key display name |
| `source_names` | JSONB | nullable | Allowed source names (null = all) |
| `is_active` | BOOLEAN | default true | Whether the key is active |
| `created_at` | TIMESTAMP | default now() | Record creation time |
| `last_used_at` | TIMESTAMP | nullable | Last time the key was used |
| `expires_at` | TIMESTAMP | nullable | Key expiration time |

## Relationships

```
sync_logs ──< failure_events      (sync_log_id FK, nullable)
failure_events ──< notification_logs  (failure_event_id FK)
webhook_endpoints ──< notification_logs  (webhook_endpoint_id FK)
```

- A **sync_log** can have zero or more **failure_events** (one per detected failure)
- A **failure_event** can have zero or more **notification_logs** (one per webhook notified)
- A **webhook_endpoint** can have many **notification_logs** across different failure events
- **sync_source_monitors** and **api_keys** are standalone tables with no foreign key relationships

## Data Retention

When `DATA_RETENTION_DAYS > 0`, a background task deletes old records in FK cascade order:

1. Delete `notification_logs` referencing old `failure_events`
2. Delete `failure_events` referencing old `sync_logs`
3. Delete `sync_logs` where `created_at` is older than the retention threshold
