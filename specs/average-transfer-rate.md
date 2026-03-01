# Spec: Average Transfer Rate

**Version:** 0.1.0
**Created:** 2026-02-20
**PRD Reference:** docs/prd.md
**Status:** Complete
**Milestone:** M1 — Foundation

## 1. Overview

Display the average transfer rate (bytes_received / duration) for each sync log as a new column in the sync table and in the detail modal. The rate is computed on-the-fly via a Jinja2 template filter — no database changes required.

### User Story

As a homelab administrator, I want to see the average transfer rate for each sync, so that I can quickly identify slow or degraded backup jobs.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Sync table displays an "Avg Rate" column showing the calculated transfer rate for each log | Must |
| AC-002 | Transfer rate is calculated as bytes_received divided by sync duration (end_time - start_time) | Must |
| AC-003 | Rate is displayed in human-readable auto-scaled format (B/s, KB/s, MB/s, GB/s) | Must |
| AC-004 | Detail modal displays the average transfer rate in the statistics grid | Must |
| AC-005 | Shows "-" when bytes_received is null or missing | Must |
| AC-006 | Shows "-" when duration is zero or start_time/end_time is missing | Must |
| AC-007 | Shows "-" for dry run entries | Must |
| AC-008 | Shows "0 B/s" when bytes_received is 0 but duration is valid | Should |
| AC-009 | A new Jinja2 template filter `format_rate` handles the formatting | Must |
| AC-010 | No database schema changes required | Must |

## 3. User Test Cases

### TC-001: Normal sync shows transfer rate

**Precondition:** Database contains a sync log with bytes_received=104857600 (100MB) and duration of 10 seconds
**Steps:**
1. Navigate to the dashboard
2. Observe the "Avg Rate" column in the sync table
**Expected Result:** The Avg Rate column shows "10.00 MB/s"
**Screenshot Checkpoint:** tests/screenshots/average-transfer-rate/step-01-normal-rate.png
**Maps to:** TBD

### TC-002: Transfer rate in detail modal

**Precondition:** Database contains a sync log with valid bytes and duration
**Steps:**
1. Click "View" on a sync log row
2. Observe the detail modal statistics
**Expected Result:** The detail modal includes an "Avg Rate" field with the calculated rate
**Screenshot Checkpoint:** tests/screenshots/average-transfer-rate/step-02-detail-modal.png
**Maps to:** TBD

### TC-003: Missing data shows dash

**Precondition:** Database contains a sync log with bytes_received=None
**Steps:**
1. Navigate to the dashboard
2. Observe the Avg Rate column for that row
**Expected Result:** Shows "-" in the Avg Rate column
**Screenshot Checkpoint:** tests/screenshots/average-transfer-rate/step-03-missing-data.png
**Maps to:** TBD

### TC-004: Dry run shows dash

**Precondition:** Database contains a dry run sync log
**Steps:**
1. Navigate to the dashboard with dry runs visible
2. Observe the Avg Rate column for the dry run row
**Expected Result:** Shows "-" in the Avg Rate column
**Screenshot Checkpoint:** tests/screenshots/average-transfer-rate/step-04-dry-run.png
**Maps to:** TBD

### TC-005: Zero bytes shows zero rate

**Precondition:** Database contains a sync log with bytes_received=0 and valid 5-second duration
**Steps:**
1. Navigate to the dashboard
2. Observe the Avg Rate column for that row
**Expected Result:** Shows "0.00 B/s"
**Screenshot Checkpoint:** tests/screenshots/average-transfer-rate/step-05-zero-bytes.png
**Maps to:** TBD

## 4. Data Model

No new database entities or fields required. This feature uses existing fields:

| Field | Type | Description |
|-------|------|-------------|
| `SyncLog.bytes_received` | `Optional[int]` | Numerator for rate calculation |
| `SyncLog.start_time` | `datetime` | Used to compute duration |
| `SyncLog.end_time` | `datetime` | Used to compute duration |
| `SyncLog.is_dry_run` | `bool` | Dry runs show "-" |

## 5. API Contract

No new API endpoints required. The existing HTMX endpoints already return all fields needed for rate calculation. The computation happens in the Jinja2 template layer.

## 6. UI Behavior

### Sync Table Column

New "Avg Rate" column added after the "Transferred" column:

```
| Source | Start | End | Duration | Total Size | Transferred | Avg Rate | Files | Actions |
```

### Detail Modal

New "Avg Rate" item added to the detail statistics grid, after "Transfer Speed".

### States

- **Normal:** "12.50 MB/s" (auto-scaled, 2 decimal places)
- **No data:** "-" (bytes_received is null)
- **No duration:** "-" (end_time or start_time missing, or duration is 0)
- **Dry run:** "-"
- **Zero bytes:** "0.00 B/s"

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| bytes_received is None | Show "-" |
| start_time or end_time is None | Show "-" |
| Duration is 0 seconds (start_time == end_time) | Show "-" (avoid division by zero) |
| Dry run sync | Show "-" |
| bytes_received is 0, duration > 0 | Show "0.00 B/s" |
| Very high rate (> 1 GB/s) | Auto-scale to GB/s |
| Very low rate (< 1 KB/s) | Show in B/s |

## 8. Dependencies

- Existing `format_bytes` filter pattern in `app/main.py` (new filter follows same pattern)
- No new Python dependencies

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-20 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
