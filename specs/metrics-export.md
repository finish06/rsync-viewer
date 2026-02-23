# Spec: Metrics Export

**Version:** 0.1.0
**Created:** 2026-02-22
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Implement a Prometheus-compatible `/metrics` endpoint and provide Grafana dashboard templates for enterprise-grade monitoring of rsync sync activity and application health.

### User Story

As a homelab administrator with a Prometheus + Grafana monitoring stack, I want rsync-viewer to expose metrics in Prometheus format, so that I can visualize sync health alongside my other infrastructure metrics and set up alerting rules.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A `/metrics` endpoint returns metrics in valid Prometheus exposition format | Must |
| AC-002 | Sync metrics are exported: `rsync_syncs_total` (counter with source, status labels), `rsync_sync_duration_seconds` (histogram), `rsync_files_transferred_total` (counter), `rsync_bytes_transferred_total` (counter) | Must |
| AC-003 | API metrics are exported: `rsync_api_requests_total` (counter with endpoint, method, status labels), `rsync_api_request_duration_seconds` (histogram) | Must |
| AC-004 | Application health metrics are exported: `rsync_db_connections_active`, `rsync_db_connections_pool_size`, `rsync_app_info` (gauge with version label) | Must |
| AC-005 | Grafana dashboard JSON templates are provided in `grafana/` directory | Should |
| AC-006 | A sync overview dashboard template exists showing sync frequency, success rate, duration trends, and bytes transferred | Should |
| AC-007 | Configurable data retention policies allow automatic cleanup of old sync logs | Should |
| AC-008 | Retention cleanup runs as a scheduled background task with configurable interval | Should |
| AC-009 | The `/metrics` endpoint does not require API key authentication (standard for Prometheus scraping) | Must |
| AC-010 | Metrics collection has minimal performance impact (< 5ms overhead per request) | Must |

## 3. User Test Cases

### TC-001: Prometheus scrape

**Precondition:** App running with metrics enabled
**Steps:**
1. Call GET `/metrics`
2. Verify response content type is `text/plain; version=0.0.4; charset=utf-8`
3. Parse response for expected metric names
**Expected Result:** Response contains all declared metrics in valid Prometheus format. Counter values increase with activity. Histograms have proper bucket distributions.
**Screenshot Checkpoint:** N/A (API)
**Maps to:** AC-001, AC-002, AC-003

### TC-002: Metrics after sync activity

**Precondition:** App running, no prior activity
**Steps:**
1. Call GET `/metrics` — note initial counter values
2. Submit 5 sync logs via POST (3 successful, 2 failed)
3. Call GET `/metrics` again
**Expected Result:** `rsync_syncs_total{status="success"}` increased by 3. `rsync_syncs_total{status="failed"}` increased by 2. Duration histogram updated with 5 observations.
**Screenshot Checkpoint:** N/A (API)
**Maps to:** AC-002

### TC-003: Grafana dashboard import

**Precondition:** Grafana instance with Prometheus data source configured
**Steps:**
1. Import `grafana/sync-overview.json` into Grafana
2. Verify dashboard panels render with data
**Expected Result:** Dashboard shows sync frequency, success/failure rates, duration trends, and bytes transferred charts. All panels have proper queries and render correctly.
**Screenshot Checkpoint:** N/A (external tool)
**Maps to:** AC-005, AC-006

### TC-004: Data retention cleanup

**Precondition:** Database has sync logs older than retention period
**Steps:**
1. Set `DATA_RETENTION_DAYS=30`
2. Trigger or wait for cleanup task
3. Query for records older than 30 days
**Expected Result:** Records older than retention period are deleted. Recent records are preserved. Cleanup is logged with count of deleted records.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-007, AC-008

## 4. Data Model

No new tables for metrics (metrics are computed at scrape time).

### Retention: No new model needed

Retention cleanup operates on existing `SyncLog` and related tables, deleting records where `created_at < now() - retention_period`.

## 5. API Contract

### GET /metrics

**Description:** Prometheus metrics endpoint.

**Authentication:** None (standard for Prometheus scraping).

**Response (200):**
Content-Type: `text/plain; version=0.0.4; charset=utf-8`

```
# HELP rsync_syncs_total Total number of rsync sync events processed
# TYPE rsync_syncs_total counter
rsync_syncs_total{source="backup-server",status="success"} 150
rsync_syncs_total{source="backup-server",status="failed"} 5

# HELP rsync_sync_duration_seconds Duration of rsync sync operations
# TYPE rsync_sync_duration_seconds histogram
rsync_sync_duration_seconds_bucket{source="backup-server",le="10"} 50
rsync_sync_duration_seconds_bucket{source="backup-server",le="60"} 120
rsync_sync_duration_seconds_bucket{source="backup-server",le="300"} 148
rsync_sync_duration_seconds_bucket{source="backup-server",le="+Inf"} 150
rsync_sync_duration_seconds_sum{source="backup-server"} 8500.5
rsync_sync_duration_seconds_count{source="backup-server"} 150

# HELP rsync_files_transferred_total Total files transferred across all syncs
# TYPE rsync_files_transferred_total counter
rsync_files_transferred_total{source="backup-server"} 4200

# HELP rsync_bytes_transferred_total Total bytes transferred across all syncs
# TYPE rsync_bytes_transferred_total counter
rsync_bytes_transferred_total{source="backup-server"} 10737418240

# HELP rsync_api_requests_total Total API requests
# TYPE rsync_api_requests_total counter
rsync_api_requests_total{endpoint="/api/v1/sync-logs",method="GET",status="200"} 500

# HELP rsync_api_request_duration_seconds API request duration
# TYPE rsync_api_request_duration_seconds histogram
rsync_api_request_duration_seconds_bucket{endpoint="/api/v1/sync-logs",method="GET",le="0.1"} 450
rsync_api_request_duration_seconds_bucket{endpoint="/api/v1/sync-logs",method="GET",le="+Inf"} 500

# HELP rsync_db_connections_active Active database connections
# TYPE rsync_db_connections_active gauge
rsync_db_connections_active 3

# HELP rsync_app_info Application information
# TYPE rsync_app_info gauge
rsync_app_info{version="1.4.0"} 1
```

## 6. Configuration

### New Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| METRICS_ENABLED | true | Enable /metrics endpoint |
| DATA_RETENTION_DAYS | 0 | Days to retain sync logs (0 = disabled / keep forever) |
| RETENTION_CLEANUP_INTERVAL_HOURS | 24 | How often to run cleanup task |

### Prometheus Configuration Example

```yaml
scrape_configs:
  - job_name: 'rsync-viewer'
    static_configs:
      - targets: ['rsync-viewer:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| /metrics called with no sync data | Return all metrics with zero values |
| Very high cardinality (many sources) | Each source gets its own label set; warn if > 100 sources |
| Prometheus scrape during high load | Metrics endpoint is lightweight, doesn't block main app |
| Retention deletes records with active references | Cascade delete notification logs and failure events for deleted sync logs |
| Retention disabled (0 days) | No cleanup runs, all data preserved |
| Metrics endpoint called with API key header | Ignore the header, return metrics normally |
| Application restart | Counters reset (standard Prometheus behavior, handled by rate() in queries) |

## 8. Dependencies

- prometheus-fastapi-instrumentator or prometheus-client library
- Existing SyncLog model for sync metrics
- Background task scheduler (for retention cleanup)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-22 | 0.1.0 | finish06 | Initial spec from TODO conversion |
