# Spec: Analytics and Reporting

**Version:** 0.1.0
**Created:** 2026-02-22
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Add analytics features for trend analysis, statistics aggregation, data export, and enhanced dashboard visualizations to help users understand sync patterns over time.

### User Story

As a homelab administrator, I want to see trends in my sync activity (frequency, file counts, transfer sizes, success rates) and export data for external analysis, so that I can identify issues and optimize my backup strategy.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A statistics API endpoint returns daily/weekly/monthly summaries for a given date range | Must |
| AC-002 | Per-source statistics are available (total syncs, success rate, avg duration, avg file count, avg bytes transferred) | Must |
| AC-003 | Sync frequency trend data is available as a time series (syncs per day/week for a source) | Must |
| AC-004 | CSV export endpoint allows downloading sync events filtered by date range and source | Must |
| AC-005 | JSON export endpoint provides full sync event details filtered by date range and source | Must |
| AC-006 | Dashboard includes interactive Chart.js charts for sync duration, file count, and bytes transferred over time | Must |
| AC-007 | Dashboard date range selector allows custom start/end dates for chart data | Must |
| AC-008 | Per-source comparison view shows side-by-side statistics for multiple sources | Should |
| AC-009 | Success/failure rate chart shows sync reliability trends per source | Should |
| AC-010 | Export endpoints support pagination for large datasets | Should |

## 3. User Test Cases

### TC-001: View daily statistics

**Precondition:** At least 30 days of sync log data in the database
**Steps:**
1. Call GET `/api/v1/analytics/summary?period=daily&start=2026-01-01&end=2026-01-31`
2. Verify response contains daily aggregates
**Expected Result:** Response includes daily summaries with total syncs, avg duration, total bytes, success count, and failure count for each day in the range.
**Screenshot Checkpoint:** N/A (API)
**Maps to:** AC-001

### TC-002: Export sync events as CSV

**Precondition:** Sync log data exists for multiple sources
**Steps:**
1. Call GET `/api/v1/analytics/export?format=csv&source=backup-server&start=2026-01-01&end=2026-01-31`
2. Open the downloaded CSV file
**Expected Result:** CSV contains headers and rows matching the filtered sync events. Fields include timestamp, source, duration, file count, bytes transferred, exit code, status.
**Screenshot Checkpoint:** N/A (download)
**Maps to:** AC-004

### TC-003: Interactive dashboard charts

**Precondition:** App running with sync data
**Steps:**
1. Navigate to the dashboard
2. Select a date range
3. View the sync duration chart
4. Hover over data points to see details
**Expected Result:** Chart.js line/bar charts display sync trends. Hovering shows tooltips with exact values. Charts update when date range changes.
**Screenshot Checkpoint:** tests/screenshots/analytics/step-03-dashboard-charts.png
**Maps to:** AC-006, AC-007

### TC-004: Per-source comparison

**Precondition:** Sync data from at least 2 sources
**Steps:**
1. Navigate to analytics section
2. Select two sources for comparison
**Expected Result:** Side-by-side statistics show total syncs, success rate, avg duration for each selected source.
**Screenshot Checkpoint:** tests/screenshots/analytics/step-04-source-comparison.png
**Maps to:** AC-008

## 4. Data Model

No new tables required. Analytics are computed from existing `SyncLog` data via aggregation queries.

### Potential Optimization (future)

If query performance becomes an issue, consider a pre-aggregated `DailyStats` table:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| source_name | String | Sync source identifier |
| date | Date | Aggregation date |
| total_syncs | Integer | Number of syncs on this date |
| successful_syncs | Integer | Syncs with exit_code 0 |
| failed_syncs | Integer | Syncs with non-zero exit_code |
| avg_duration_seconds | Float | Average sync duration |
| total_bytes_transferred | BigInteger | Sum of bytes transferred |
| total_files_transferred | Integer | Sum of files transferred |
| created_at | DateTime | When this aggregate was computed |

## 5. API Contract

### GET /api/v1/analytics/summary

**Description:** Get aggregated sync statistics for a date range.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| period | String | Yes | `daily`, `weekly`, or `monthly` |
| start | Date | Yes | Start date (ISO 8601) |
| end | Date | Yes | End date (ISO 8601) |
| source | String | No | Filter by source name |

**Response (200):**
```json
{
  "period": "daily",
  "start": "2026-01-01",
  "end": "2026-01-31",
  "data": [
    {
      "date": "2026-01-01",
      "total_syncs": 5,
      "successful_syncs": 4,
      "failed_syncs": 1,
      "avg_duration_seconds": 120.5,
      "total_bytes_transferred": 1048576,
      "total_files_transferred": 42
    }
  ]
}
```

### GET /api/v1/analytics/sources

**Description:** Get per-source aggregate statistics.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| start | Date | No | Start date filter |
| end | Date | No | End date filter |

**Response (200):**
```json
[
  {
    "source_name": "backup-server",
    "total_syncs": 150,
    "success_rate": 0.95,
    "avg_duration_seconds": 85.3,
    "avg_files_transferred": 28,
    "avg_bytes_transferred": 524288,
    "last_sync_at": "2026-02-22T10:00:00Z"
  }
]
```

### GET /api/v1/analytics/export

**Description:** Export sync events in CSV or JSON format.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| format | String | Yes | `csv` or `json` |
| start | Date | No | Start date filter |
| end | Date | No | End date filter |
| source | String | No | Filter by source name |
| limit | Integer | No | Max records (default 10000) |
| offset | Integer | No | Pagination offset |

**Response (200):** File download (CSV) or JSON array.

**Error Responses:**
- `400` - Invalid date range or format
- `401` - Missing or invalid API key

## 6. UI Behavior

### Dashboard Charts Section

- **Chart types:** Line chart for duration trends, bar chart for file counts, area chart for bytes transferred
- **Controls:** Date range picker, source filter dropdown, period selector (daily/weekly/monthly)
- **Loading:** Skeleton placeholder while data loads via HTMX
- **Empty:** "No sync data for the selected period" message
- **Interaction:** Tooltip on hover showing exact values, click to filter

### Export Controls

- **Location:** Analytics section of dashboard
- **Controls:** Date range, source filter, format selector (CSV/JSON), download button
- **Feedback:** Loading spinner during export generation, download triggers automatically

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| No data for selected date range | Return empty data array, charts show "No data" message |
| Very large export (100k+ rows) | Stream response, enforce max limit, suggest narrower date range |
| Source name with special characters | URL-encode in query params, handle in filters |
| Date range spans months/years | Correctly aggregate across boundaries |
| Concurrent export requests | Handle without blocking other API requests |
| Missing duration data on old records | Exclude from avg calculations, don't error |

## 8. Dependencies

- Existing SyncLog model and data
- Chart.js library (frontend)
- Performance optimization spec (for large dataset handling, future)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-22 | 0.1.0 | finish06 | Initial spec from TODO conversion |
