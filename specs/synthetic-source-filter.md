# Spec: Synthetic Source Filter

**Version:** 0.1.0
**Created:** 2026-03-05
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

The synthetic monitoring system creates periodic test sync logs with source name `__synthetic_check`. These logs pollute the main dashboard table, analytics charts, and API responses, making it harder for operators to see real sync activity. This feature excludes synthetic data from all default views and API responses, with a toggle to view synthetic data in isolation.

### User Story

As a homelab administrator, I want synthetic monitoring logs hidden from my dashboard and analytics by default, so that I only see real sync activity unless I explicitly choose to inspect synthetic checks.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | The sync log table (`/htmx/sync-table`) excludes `__synthetic_check` source by default | Must |
| AC-002 | The analytics charts (`/htmx/charts`) exclude `__synthetic_check` source by default | Must |
| AC-003 | The API endpoints (`/api/v1/sync-logs`, `/api/v1/analytics/summary`, `/api/v1/analytics/sources`, `/api/v1/analytics/export`) exclude `__synthetic_check` by default | Must |
| AC-004 | A "Show synthetic checks" toggle appears on the dashboard log table view (default OFF) | Must |
| AC-005 | A "Show synthetic checks" toggle appears on the analytics view (default OFF) | Must |
| AC-006 | When the toggle is ON, the view shows **only** synthetic data — all other sources are hidden | Must |
| AC-007 | The source filter dropdown never lists `__synthetic_check` regardless of toggle state | Must |
| AC-008 | The API accepts a `synthetic` query parameter (`hide` / `only` / `show`) defaulting to `hide` | Must |
| AC-009 | The shared `apply_sync_filters()` function handles synthetic filtering consistently across all query paths | Must |
| AC-010 | When the toggle is ON with date range filters active, both filters compose (synthetic data within the selected date range) | Should |
| AC-011 | The index page source dropdown (server-side rendered) also excludes `__synthetic_check` | Must |

## 3. User Test Cases

### TC-001: Default dashboard hides synthetic logs

**Precondition:** Database contains both real sync logs and `__synthetic_check` logs
**Steps:**
1. Navigate to the dashboard (`/`)
2. Observe the sync log table
**Expected Result:** No rows with `__synthetic_check` source appear. The "Show synthetic checks" toggle is visible and OFF.
**Screenshot Checkpoint:** tests/screenshots/synthetic-filter/step-01-default-hidden.png
**Maps to:** TBD

### TC-002: Toggle shows only synthetic data

**Precondition:** Database contains both real sync logs and `__synthetic_check` logs
**Steps:**
1. Navigate to the dashboard
2. Enable the "Show synthetic checks" toggle
3. Observe the sync log table
**Expected Result:** Only `__synthetic_check` rows are shown. Real sync logs are hidden.
**Screenshot Checkpoint:** tests/screenshots/synthetic-filter/step-02-toggle-on.png
**Maps to:** TBD

### TC-003: Analytics excludes synthetic by default

**Precondition:** Database has synthetic and real sync logs over the past 7 days
**Steps:**
1. Navigate to the analytics view
2. Select "Last 7 days"
3. Observe charts and source comparison
**Expected Result:** Charts reflect only real sync data. `__synthetic_check` does not appear in source comparison cards or the source dropdown.
**Screenshot Checkpoint:** tests/screenshots/synthetic-filter/step-03-analytics-default.png
**Maps to:** TBD

### TC-004: Analytics toggle shows only synthetic

**Precondition:** Database has synthetic and real sync logs
**Steps:**
1. Navigate to the analytics view
2. Enable the "Show synthetic checks" toggle
3. Observe charts
**Expected Result:** Charts show only synthetic check data.
**Screenshot Checkpoint:** tests/screenshots/synthetic-filter/step-04-analytics-synthetic.png
**Maps to:** TBD

### TC-005: Source dropdown never shows synthetic

**Precondition:** Database has `__synthetic_check` logs
**Steps:**
1. Navigate to the dashboard
2. Open the source filter dropdown
3. Toggle "Show synthetic checks" ON
4. Open the source filter dropdown again
**Expected Result:** `__synthetic_check` never appears in the dropdown in either state.
**Screenshot Checkpoint:** tests/screenshots/synthetic-filter/step-05-dropdown-clean.png
**Maps to:** TBD

### TC-006: API excludes synthetic by default

**Precondition:** Database has synthetic and real sync logs
**Steps:**
1. Call `GET /api/v1/sync-logs` without parameters
2. Call `GET /api/v1/sync-logs?synthetic=only`
3. Call `GET /api/v1/sync-logs?synthetic=show`
**Expected Result:** (1) returns no synthetic logs, (2) returns only synthetic logs, (3) returns all logs including synthetic.
**Maps to:** TBD

## 4. Data Model

No schema changes required. The feature filters on the existing `SyncLog.source_name` column using the constant `SYNTHETIC_SOURCE_NAME = "__synthetic_check"` already defined in `app/services/synthetic_check.py`.

## 5. API Contract

### Modified: GET `/api/v1/sync-logs`

**New query parameter:**

| Param | Type | Default | Values |
|-------|------|---------|--------|
| `synthetic` | string | `hide` | `hide` — exclude `__synthetic_check` (default) |
| | | | `only` — return only `__synthetic_check` |
| | | | `show` — no filtering, return all |

### Modified: GET `/api/v1/sync-logs/sources`

**Changed behavior:** Excludes `__synthetic_check` from the returned source list unconditionally.

### Modified: GET `/api/v1/analytics/summary`

**New query parameter:** `synthetic` (same values as above, default `hide`)

### Modified: GET `/api/v1/analytics/sources`

**Changed behavior:** Excludes `__synthetic_check` from returned source statistics by default. Accepts `synthetic` parameter.

### Modified: GET `/api/v1/analytics/export`

**New query parameter:** `synthetic` (same values as above, default `hide`)

## 6. UI Behavior

### Dashboard sync table

- Toggle location: filter bar area, alongside existing "Show Dry Runs" toggle
- Label: "Show synthetic checks" or similar user-friendly text
- Default state: OFF
- Behavior when ON: table shows only `__synthetic_check` rows; other filters (date range) still compose
- Toggle fires HTMX request to reload the table with `synthetic=only` parameter

### Analytics view

- Toggle location: filter controls area, alongside source dropdown and date pickers
- Label: Same as dashboard toggle
- Default state: OFF
- Behavior when ON: charts and source comparison show only synthetic data
- Toggle fires HTMX request to reload charts with `synthetic=only` parameter

### States

- **Toggle OFF (default):** Normal view, synthetic data invisible
- **Toggle ON:** Synthetic-only view, real data invisible
- **No synthetic data exists:** Toggle ON shows empty state, toggle has no visual change

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| No synthetic logs exist in database | Toggle appears but switching ON shows empty table/charts |
| Synthetic toggle ON + source filter selected | Source filter is ignored (synthetic overrides), or source filter is cleared when toggle activates |
| Synthetic toggle ON + date range filter | Filters compose — shows synthetic logs within date range |
| API `synthetic=only` + `source_name=other` | `synthetic=only` takes precedence, `source_name` is ignored |
| Source dropdown population after toggle | Dropdown content unchanged — `__synthetic_check` never listed |

## 8. Dependencies

- `SYNTHETIC_SOURCE_NAME` constant from `app/services/synthetic_check.py`
- `apply_sync_filters()` in `app/services/sync_filters.py` — add synthetic filter parameter
- Existing filter UI patterns (dry run toggle) as implementation reference

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-05 | 0.1.0 | Claude | Initial spec from /add:spec interview |
