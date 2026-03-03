# Glossary

Domain terminology used throughout Rsync Log Viewer.

| Term | Definition |
|------|-----------|
| **Sync Log** | A record of a single rsync execution, including raw output, parsed statistics, and metadata. Created via `POST /api/v1/sync-logs`. |
| **Source Name** | A user-defined label identifying the origin of a sync job (e.g., `nas-backup`, `photos-mirror`). Used for filtering and grouping. |
| **Exit Code** | The numeric return code from rsync. `0` = success, non-zero = error. Used by failure detection to trigger notifications. |
| **Dry Run** | An rsync execution with `--dry-run` / `-n` flag. Simulates the transfer without moving data. Detected automatically by the parser. |
| **Speedup** | Rsync's efficiency ratio: `total_size / bytes_sent`. Higher values mean less data was transferred relative to total size. |
| **Stale Sync** | A monitored source that has not reported a sync within its expected interval. Triggers a webhook notification. |
| **Monitor** | A configuration that watches a specific source for sync activity. Tracks `expected_interval` and `last_sync_at` to detect stale syncs. |
| **Failure Event** | A sync log with a non-zero exit code or a stale sync detection. Triggers the notification pipeline. |
| **Webhook Endpoint** | A configured URL that receives POST notifications when failures or stale syncs are detected. Supports generic webhooks and Discord. |
| **Notification Log** | A record of each notification attempt, including delivery status, response code, and retry count. Viewable in the notification history dashboard. |
| **Synthetic Check** | A periodic self-test that submits a known-good sync log to the API and verifies the round-trip. Used to confirm the ingestion pipeline is healthy. |
| **API Key** | A bearer token used to authenticate API requests. Hashed with bcrypt and stored per-user. Prefixed with `rsv_`. |
| **Hub** | The central Rsync Log Viewer instance that receives, stores, and displays sync logs from one or more clients. |
| **Client** | A remote rsync container or script that executes sync jobs and ships logs to the hub via the API. |
| **OIDC** | OpenID Connect — a federated authentication protocol. Rsync Log Viewer supports OIDC SSO via providers like PocketId, Authelia, or Keycloak. |
