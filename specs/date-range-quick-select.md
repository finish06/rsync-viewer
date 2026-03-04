# Spec: Date Range Quick Select

**Version:** 0.2.0
**Created:** 2026-02-20
**PRD Reference:** docs/prd.md
**Status:** Implementing
**Milestone:** M1 — Foundation

## 1. Overview

Add quick-select date range buttons to the dashboard filter bar, allowing users to rapidly switch between common time ranges (Last 7 Days, Last 30 Days, Max Records) without manually entering dates. A "Custom" option reveals the existing start/end date pickers for arbitrary ranges. The default view on dashboard load is "Last 7 Days".

**v0.2.0 additions:** The same quick-select buttons must appear on the Analytics and Notifications tabs for UI consistency. Analytics currently has bare date inputs with no presets (defaults to 30 days via JS). Notifications has no date filtering at all. Both tabs should match the Sync Logs pattern.

### User Story

As a homelab administrator, I want quick-select buttons for common date ranges, so that I can filter sync logs faster without manually entering dates every time.

As a homelab administrator, I want the same quick-select date range buttons on the Analytics and Notifications tabs, so that I have a consistent filtering experience across all dashboard views.

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
| AC-011 | The Analytics tab displays quick-select buttons (Last 7 Days, Last 30 Days, Max, Custom) above the existing Period/From/To/Source filter form | Must |
| AC-012 | Clicking a quick-select button on Analytics auto-populates the From/To date inputs and triggers a chart refresh without requiring a manual "Update" click | Must |
| AC-013 | The Analytics "Custom" button activates the From/To date inputs for manual entry; user clicks "Update" to apply | Must |
| AC-014 | The Analytics tab defaults to "Last 30 Days" selected on load (preserves current behavior) | Must |
| AC-015 | The Notifications tab displays quick-select buttons (Last 7 Days, Last 30 Days, Max, Custom) above the existing Status/Webhook/Source filter form | Must |
| AC-016 | The `GET /htmx/notifications` endpoint accepts optional `date_from` and `date_to` query parameters, filtering `NotificationLog.created_at` accordingly | Must |
| AC-017 | Clicking a quick-select button on Notifications triggers an HTMX reload with the appropriate date range | Must |
| AC-018 | The Notifications tab defaults to "Last 7 Days" on initial load | Must |
| AC-019 | Date range selection persists through Notifications pagination (date params included in prev/next HTMX links) | Should |
| AC-020 | All quick-select buttons across all three tabs use the existing `.quick-select` and `.quick-select-btn` CSS classes | Must |

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

### TC-006: Analytics quick-select — Last 7 Days

**Precondition:** User is on the dashboard, Analytics tab selected. Data exists spanning 30+ days.
**Steps:**
1. Click "Last 7 Days" quick-select button
**Expected Result:** From date is set to 7 days ago, To date is set to today. Charts refresh with 7-day data. "Last 7 Days" button is highlighted. Source comparison updates.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-06-analytics-7d.png
**Maps to:** TBD

### TC-007: Analytics quick-select — default is Last 30 Days

**Precondition:** User navigates to dashboard and clicks Analytics tab
**Steps:**
1. Observe the quick-select buttons on initial load
**Expected Result:** "Last 30 Days" button is highlighted. From/To inputs show last 30 days. Charts display 30-day data (same as current behavior).
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-07-analytics-default.png
**Maps to:** TBD

### TC-008: Analytics quick-select — Max

**Precondition:** User is on Analytics tab
**Steps:**
1. Click "Max" quick-select button
**Expected Result:** From/To date fields are cleared. Charts show all historical data. "Max" button is highlighted.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-08-analytics-max.png
**Maps to:** TBD

### TC-009: Notifications quick-select — default is Last 7 Days

**Precondition:** User navigates to dashboard and clicks Notifications tab. Notifications exist spanning 30+ days.
**Steps:**
1. Observe the initial load
**Expected Result:** "Last 7 Days" button is highlighted. Only notifications from the last 7 days are shown. Filter dropdowns (Status, Webhook, Source) remain functional.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-09-notifications-default.png
**Maps to:** TBD

### TC-010: Notifications quick-select — Last 30 Days

**Precondition:** User is on Notifications tab
**Steps:**
1. Click "Last 30 Days" quick-select button
**Expected Result:** Notification list reloads via HTMX showing last 30 days. "Last 30 Days" button is highlighted. Pagination reflects new total count.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-10-notifications-30d.png
**Maps to:** TBD

### TC-011: Notifications date range persists through pagination

**Precondition:** User is on Notifications tab with "Last 30 Days" selected, more than 20 notifications exist in the range
**Steps:**
1. Click "Next" pagination button
**Expected Result:** Page 2 shows notifications still filtered to last 30 days. Quick-select button remains highlighted.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-11-notifications-paginate.png
**Maps to:** TBD

### TC-012: Notifications quick-select combined with status filter

**Precondition:** User is on Notifications tab with notifications of mixed statuses
**Steps:**
1. Click "Last 30 Days" quick-select button
2. Select "failed" from the Status dropdown
3. Click "Filter"
**Expected Result:** Only failed notifications from the last 30 days are shown. Both the date range and status filter apply together.
**Screenshot Checkpoint:** tests/screenshots/date-range-quick-select/step-12-notifications-combined.png
**Maps to:** TBD

## 4. Data Model

No new database entities required. This feature operates on the existing `SyncLog` model using existing `start_time` field for date filtering.

### Existing Fields Used

| Field | Type | Description |
|-------|------|-------------|
| `SyncLog.start_time` | `datetime` | Used for date range filtering |

## 5. API Contract

No new API endpoints required for Sync Logs or Analytics. The existing endpoints already accept date parameters. The quick-select buttons compute date values client-side and pass them to the existing endpoints.

### Modified Behavior: HTMX Table Endpoint (Sync Logs — existing)

**Existing:** `GET /htmx/sync-table?start_date=...&end_date=...&show_dry_run=...&hide_empty=...`

**Added parameter:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `load_all` | bool | false | When true, return all matching records instead of paginated results |

### Modified: GET /htmx/notifications (v0.2.0)

**New query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date_from` | str (YYYY-MM-DD) | No | Filter notifications on or after this date (inclusive) |
| `date_to` | str (YYYY-MM-DD) | No | Filter notifications on or before this date (end of day, inclusive) |

These combine with existing `status`, `webhook_name`, `source_name`, `offset`, `limit` parameters via AND logic. Pagination prev/next links must include `date_from` and `date_to` if set.

### Unchanged: Analytics API endpoints

`GET /api/v1/analytics/summary` and `GET /api/v1/analytics/sources` already accept `start` and `end` parameters. No backend change needed — only the frontend quick-select buttons are added.

## 6. UI Behavior

### Sync Logs Tab Layout (existing — unchanged)

```
[ Last 7 Days ] [ Last 30 Days ] [ Max ] [ Custom ]

Source: [All Sources ▼]  Dry Runs: [Hide ▼]  Empty Runs: [Hide ▼]  [Filter] [Reset]
```

Default: Last 7 Days. "Custom" reveals start/end date inputs.

### Analytics Tab Layout (v0.2.0)

```
[ Last 7 Days ] [ Last 30 Days ] [ Max ] [ Custom ]            ← NEW

Period: [Daily ▼]  From: [____]  To: [____]  Source: [All ▼]  [Update]
```

**Behavior:**
- Quick-select buttons set the From/To date inputs and auto-submit (trigger `fetchAnalytics()`)
- "Custom" highlights the button but does NOT auto-submit — user sets dates manually and clicks "Update"
- "Max" clears both date fields (API treats missing dates as unbounded)
- Default on load: "Last 30 Days" (preserves current 30-day default)
- Export CSV/JSON links update to reflect the current date range

### Notifications Tab Layout (v0.2.0)

```
[ Last 7 Days ] [ Last 30 Days ] [ Max ] [ Custom ]            ← NEW

Status: [All ▼]  Webhook: [All ▼]  Source: [All ▼]  [Filter]
```

**Behavior:**
- Quick-select buttons compute `date_from`/`date_to` client-side and include them in the HTMX `hx-get` request
- "Custom" reveals From/To date input fields inline with the existing filter form
- Other presets hide the date inputs (dates are computed from the button)
- Default on load: "Last 7 Days"
- Pagination prev/next links include `date_from` and `date_to` params so the range persists across pages
- All existing filters (status, webhook, source) combine with date range via AND logic

### States

- **Loading:** Table/charts show loading indicator while HTMX fetches filtered results
- **Empty:** Tab-appropriate empty message (e.g., "No notifications found in the selected date range.")
- **Error:** Standard error handling for failed HTMX requests
- **Max with overflow (Sync Logs):** When Max is selected and total records > 50, show "Load All (N remaining)" button below the table

### Screenshot Checkpoints

| Step | Description | Path |
|------|-------------|------|
| 1 | Sync Logs — Last 7 Days active (default) | tests/screenshots/date-range-quick-select/step-01-default-load.png |
| 2 | Sync Logs — Last 30 Days selected | tests/screenshots/date-range-quick-select/step-02-last-30-days.png |
| 3 | Sync Logs — Max with Load All button | tests/screenshots/date-range-quick-select/step-03-max-load-all.png |
| 4 | Sync Logs — Custom with date pickers visible | tests/screenshots/date-range-quick-select/step-04-custom-range.png |
| 5 | Analytics — Last 7 Days selected | tests/screenshots/date-range-quick-select/step-05-analytics-7d.png |
| 6 | Analytics — Last 30 Days default on load | tests/screenshots/date-range-quick-select/step-06-analytics-default.png |
| 7 | Notifications — Last 7 Days default on load | tests/screenshots/date-range-quick-select/step-07-notifications-default.png |
| 8 | Notifications — Last 30 Days with pagination | tests/screenshots/date-range-quick-select/step-08-notifications-30d.png |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| No logs exist in the last 7 days | Table shows empty state; "Last 7 Days" still highlighted as active |
| Fewer than 50 logs exist when "Max" selected | All logs shown, no "Load All" button displayed |
| User switches from "Custom" with dates to "Last 7 Days" | Date picker inputs are hidden, date values are overridden by the 7-day calculation |
| User clicks "Reset" while a quick-select is active | Resets to default "Last 7 Days" selection |
| Browser timezone differs from server timezone | Date calculations happen client-side using local timezone; server compares against UTC start_time |
| Notifications: invalid date_from/date_to format | Ignore invalid dates, show unfiltered results |
| Notifications: date_from after date_to | Swap dates silently or ignore, show unfiltered results |
| Notifications: quick-select + status filter combined | Both filters apply via AND logic |
| Analytics: "Max" with very large dataset | Charts render all data points; performance acceptable for homelab scale (~1000 logs/day) |
| Switching tabs preserves quick-select per tab | Each tab maintains its own active quick-select state independently |

## 8. Dependencies

- Existing HTMX filter mechanism (`/htmx/sync-table`, `/htmx/charts`)
- Existing `.quick-select` and `.quick-select-btn` CSS classes (already theme-aware)
- Analytics partial template (`app/templates/partials/analytics.html`)
- Notifications partial template (`app/templates/partials/notifications_list.html`)
- Notifications HTMX endpoint (`app/routes/dashboard.py` — `htmx_notifications`)
- No new backend dependencies

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-20 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
| 2026-03-04 | 0.2.0 | finish06 + Claude | AC-011–AC-020, TC-006–TC-012: Add quick-select buttons to Analytics and Notifications tabs |
