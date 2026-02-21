# Spec: Date Range Quick Select

**Version:** 0.1.0
**Created:** 2026-02-20
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Add quick-select date range buttons to the dashboard filter bar, allowing users to rapidly switch between common time ranges (Last 7 Days, Last 30 Days, Max Records) without manually entering dates. A "Custom" option reveals the existing start/end date pickers for arbitrary ranges. The default view on dashboard load is "Last 7 Days".

### User Story

As a homelab administrator, I want quick-select buttons for common date ranges, so that I can filter sync logs faster without manually entering dates every time.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Dashboard displays pill-style toggle buttons: "Last 7 Days", "Last 30 Days", "Max", "Custom" above the existing filters | Must |
| AC-002 | Selecting "Last 7 Days" filters the table and charts to only show logs from the past 7 days | Must |
| AC-003 | Selecting "Last 30 Days" filters the table and charts to only show logs from the past 30 days | Must |
| AC-004 | Selecting "Max" loads the first 50 records (all time, no date filter) and displays a "Load All" button if more records exist | Must |
| AC-005 | Clicking "Load All" on the Max view fetches and displays all remaining records | Must |
| AC-006 | Selecting "Custom" reveals the existing start_date and end_date pickers | Must |
| AC-007 | The dashboard defaults to "Last 7 Days" on initial page load | Must |
| AC-008 | The active quick-select button is visually highlighted to indicate current selection | Should |
| AC-009 | Selecting a quick-select option updates both the sync table and charts simultaneously | Must |
| AC-010 | Quick select works in combination with other filters (source, dry run, empty runs) | Should |

## 3. User Test Cases

### TC-001: Default load shows last 7 days

**Precondition:** Database contains sync logs spanning more than 7 days
**Steps:**
1. Navigate to the dashboard
2. Observe the quick-select buttons and table content
**Expected Result:** "Last 7 Days" button is highlighted. Table and charts show only logs from the past 7 days.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-01-default-load.png
**Maps to:** TBD

### TC-002: Switch to Last 30 Days

**Precondition:** Dashboard loaded with default "Last 7 Days" view
**Steps:**
1. Click the "Last 30 Days" pill button
2. Observe table and chart updates
**Expected Result:** "Last 30 Days" button becomes highlighted. Table and charts update to show logs from the past 30 days.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-02-last-30-days.png
**Maps to:** TBD

### TC-003: Max Records with Load All

**Precondition:** Database contains more than 50 sync logs
**Steps:**
1. Click the "Max" pill button
2. Observe the first 50 records load
3. Click the "Load All" button
4. Observe remaining records load
**Expected Result:** Initially 50 records shown with a "Load All" button visible. After clicking "Load All", all records are displayed and the "Load All" button disappears.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-03-max-load-all.png
**Maps to:** TBD

### TC-004: Custom date range

**Precondition:** Dashboard loaded
**Steps:**
1. Click the "Custom" pill button
2. Observe the date picker inputs appear
3. Enter a start and end date
4. Click "Filter"
**Expected Result:** "Custom" button is highlighted. Start/end date pickers are visible. Table and charts filter to the selected custom range.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-04-custom-range.png
**Maps to:** TBD

### TC-005: Quick select combined with source filter

**Precondition:** Database contains logs from multiple sources spanning 30+ days
**Steps:**
1. Select "Last 30 Days" quick select
2. Select a specific source from the source dropdown
3. Click "Filter"
**Expected Result:** Table shows only logs from the selected source within the last 30 days.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-05-combined-filters.png
**Maps to:** TBD

## 4. Data Model

No new database entities required. This feature operates on the existing `SyncLog` model using existing `start_time` field for date filtering.

### Existing Fields Used

| Field | Type | Description |
|-------|------|-------------|
| `SyncLog.start_time` | `datetime` | Used for date range filtering |

## 5. API Contract

No new API endpoints required. The existing `/htmx/sync-table` and `/htmx/charts` endpoints already accept `start_date` and `end_date` query parameters. The quick-select buttons compute date values client-side and pass them to the existing endpoints.

### Modified Behavior: HTMX Table Endpoint

The existing HTMX table endpoint needs to support a `load_all=true` parameter to bypass the default pagination limit when the user clicks "Load All" on the Max view.

**Existing:** `GET /htmx/sync-table?start_date=...&end_date=...&show_dry_run=...&hide_empty=...`

**Added parameter:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `load_all` | bool | false | When true, return all matching records instead of paginated results |

## 6. UI Behavior

### Layout

Pill-style toggle buttons rendered as a button group above the existing filter bar:

```
[ Last 7 Days ] [ Last 30 Days ] [ Max ] [ Custom ]

Source: [All Sources ▼]  Dry Runs: [Hide ▼]  Empty Runs: [Hide ▼]  [Filter] [Reset]
```

When "Custom" is selected, the existing start_date and end_date inputs become visible within the filter bar. When any other option is selected, the date inputs are hidden.

### States

- **Loading:** Table shows loading indicator while HTMX fetches filtered results
- **Empty:** If no logs match the selected date range, show existing empty state
- **Error:** Standard error handling for failed HTMX requests
- **Max with overflow:** When Max is selected and total records > 50, show "Load All (N remaining)" button below the table

### Screenshot Checkpoints

| Step | Description | Path |
|------|-------------|------|
| 1 | Default load — Last 7 Days active | tests/screenshots/date-range-quick-select/step-01-default-load.png |
| 2 | Last 30 Days selected | tests/screenshots/date-range-quick-select/step-02-last-30-days.png |
| 3 | Max with Load All button | tests/screenshots/date-range-quick-select/step-03-max-load-all.png |
| 4 | Custom with date pickers visible | tests/screenshots/date-range-quick-select/step-04-custom-range.png |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| No logs exist in the last 7 days | Table shows empty state; "Last 7 Days" still highlighted as active |
| Fewer than 50 logs exist when "Max" selected | All logs shown, no "Load All" button displayed |
| User switches from "Custom" with dates to "Last 7 Days" | Date picker inputs are hidden, date values are overridden by the 7-day calculation |
| User clicks "Reset" while a quick-select is active | Resets to default "Last 7 Days" selection |
| Browser timezone differs from server timezone | Date calculations happen client-side using local timezone; server compares against UTC start_time |

## 8. Dependencies

- Existing HTMX filter mechanism (`/htmx/sync-table`, `/htmx/charts`)
- Existing CSS styles for buttons (may need new pill-button styles)
- No new backend dependencies

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-20 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
