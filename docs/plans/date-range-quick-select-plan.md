# Implementation Plan: Date Range Quick Select

**Spec Version:** 0.1.0
**Spec:** specs/date-range-quick-select.md
**Created:** 2026-02-20
**Team Size:** Solo
**Estimated Duration:** 4-5 hours

## Overview

Add pill-style quick-select date range buttons (Last 7 Days, Last 30 Days, Max, Custom) above the existing dashboard filter bar. Default to "Last 7 Days" on load. "Max" loads first 50 records with a "Load All" button to fetch the rest. "Custom" reveals the existing date picker inputs.

## Objectives

- Reduce clicks needed to filter by common date ranges
- Default dashboard to a useful 7-day window instead of showing everything
- Support "Load All" for users who want the full dataset

## Success Criteria

- All 10 acceptance criteria implemented
- Existing filter behavior preserved
- Quick select integrates with source/dry-run/empty-run filters
- No regressions in existing dashboard functionality

## Acceptance Criteria Analysis

### AC-001: Pill-style toggle buttons above existing filters
- **Complexity:** Simple
- **Effort:** 1h
- **Tasks:** TASK-001, TASK-002
- **Testing:** Visual inspection, unit test for template rendering

### AC-002 / AC-003: Last 7 Days and Last 30 Days filtering
- **Complexity:** Simple
- **Effort:** 30min
- **Tasks:** TASK-003
- **Testing:** Client-side date calculation verified by integration tests

### AC-004: Max loads first 50 with "Load All" button
- **Complexity:** Medium
- **Effort:** 1.5h
- **Tasks:** TASK-004, TASK-005
- **Dependencies:** Backend must return total count (already does)
- **Testing:** Backend test for `load_all` param, template test for button visibility

### AC-005: "Load All" fetches remaining records
- **Complexity:** Medium
- **Effort:** 1h
- **Tasks:** TASK-005, TASK-006
- **Dependencies:** TASK-004
- **Testing:** Backend test confirming no pagination when `load_all=true`

### AC-006: Custom reveals date pickers
- **Complexity:** Simple
- **Effort:** 30min
- **Tasks:** TASK-003
- **Testing:** JS logic test, visual confirmation

### AC-007: Default to Last 7 Days on load
- **Complexity:** Simple
- **Effort:** 30min
- **Tasks:** TASK-007
- **Testing:** Integration test confirming default parameters

### AC-008: Active button highlighted
- **Complexity:** Simple
- **Effort:** 15min (included in TASK-002)
- **Testing:** CSS class toggle verified

### AC-009: Updates both table and charts simultaneously
- **Complexity:** Simple
- **Effort:** Included in TASK-003
- **Testing:** Verify both HTMX targets receive requests

### AC-010: Works with other filters
- **Complexity:** Simple
- **Effort:** Included in TASK-003
- **Testing:** Combined filter integration test

## Implementation Phases

### Phase 1: Backend — Add `load_all` parameter (30min)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-001 | Add `load_all` query parameter to `/htmx/sync-table` endpoint in `app/main.py`. When `true`, set limit to `None` (return all matching records). Keep existing pagination behavior as default. | 30min | None | AC-004, AC-005 |

**Files Modified:**
- `app/main.py` — modify `htmx_sync_table` handler

**Details:**
- Add `load_all: bool = Query(False)` parameter
- When `load_all=True`, skip offset/limit (or set limit very high)
- No changes needed to the charts endpoint (charts already fetch latest 50)

### Phase 2: Frontend — Quick select UI (2h)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-002 | Add pill button HTML to `index.html` — a `.quick-select` button group with 4 buttons above the existing filter form. | 30min | None | AC-001, AC-008 |
| TASK-003 | Add JavaScript logic to `index.html` for quick-select behavior: compute date ranges, toggle active state, show/hide date pickers for Custom, trigger HTMX requests to both table and charts. | 1h | TASK-002 | AC-002, AC-003, AC-006, AC-009, AC-010 |
| TASK-004 | Update `partials/sync_table.html` to conditionally render a "Load All (N remaining)" button when in Max mode and total > displayed count. The button triggers an HTMX request with `load_all=true`. | 30min | TASK-001 | AC-004, AC-005 |

**Files Modified:**
- `app/templates/index.html` — add button group + JS logic
- `app/templates/partials/sync_table.html` — add "Load All" button

**JavaScript Details:**
- `selectRange(range)` function that:
  - Sets active class on clicked button
  - Computes `start_date` as ISO string (today minus N days) for 7d/30d
  - Clears dates for Max mode
  - Shows/hides date inputs for Custom
  - Builds query params including other filter values
  - Fires `htmx.ajax('GET', ...)` to both `/htmx/charts` and `/htmx/sync-table`
- On page load, auto-call `selectRange('7d')`

### Phase 3: Styling (30min)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-005 | Add CSS for `.quick-select` button group: pill-style buttons with active state highlighting, responsive layout. Support both light and dark themes. | 30min | TASK-002 | AC-001, AC-008 |

**Files Modified:**
- `app/static/css/styles.css` — add quick-select button styles

**CSS Details:**
- `.quick-select` container: flex row, gap, margin-bottom
- `.quick-select button`: pill border-radius, border, background transparent
- `.quick-select button.active`: primary color background, white text
- Dark mode overrides via `[data-theme="dark"]`
- `.load-all-btn`: styled button below table for Max mode

### Phase 4: Default behavior + integration (30min)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-006 | Update default HTMX triggers on page load in `index.html` to use 7-day date range instead of no date filter. Update `resetFilters()` to reset to "Last 7 Days" instead of clearing all filters. | 30min | TASK-003 | AC-007 |

**Files Modified:**
- `app/templates/index.html` — modify initial `hx-get` URLs and reset function

**Details:**
- The current `hx-trigger="load"` on charts and table containers uses default params with no dates
- Change to: either compute 7-day range server-side in the template context, or trigger via JS on DOMContentLoaded
- Simplest approach: remove `hx-trigger="load"` from the containers, let the JS `selectRange('7d')` on DOMContentLoaded handle the initial load

### Phase 5: Pass total count to template for "Load All" (15min)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-007 | Ensure the HTMX sync-table endpoint passes `total`, `offset`, `limit`, and current filter params to the template so the "Load All" button can construct the correct HTMX request URL. | 15min | TASK-001 | AC-004, AC-005 |

**Files Modified:**
- `app/main.py` — ensure template context includes all needed values (likely already does based on existing pagination)
- `app/templates/partials/sync_table.html` — use total/limit to conditionally show button

## Effort Summary

| Phase | Estimated | Tasks |
|-------|-----------|-------|
| Phase 1: Backend | 30min | TASK-001 |
| Phase 2: Frontend | 2h | TASK-002, TASK-003, TASK-004 |
| Phase 3: Styling | 30min | TASK-005 |
| Phase 4: Defaults | 30min | TASK-006 |
| Phase 5: Template data | 15min | TASK-007 |
| **Total** | **~4h** | **7 tasks** |

## Dependencies

### Internal
- No upstream features required
- Existing HTMX endpoints already support `start_date`/`end_date` filtering
- Existing pagination returns `total` count

### External
- None

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Timezone mismatch between JS date calculation and server filtering | Medium | Low | Use ISO date strings, document timezone behavior |
| "Load All" with very large dataset causes slow response | Low | Medium | Acceptable for homelab scale; could add upper limit later |
| Chart.js re-render on quick select causes flicker | Low | Low | HTMX swap handles this cleanly already |

## Testing Strategy

Since maturity is POC, formal TDD is optional. Recommended tests:

1. **Backend unit test:** `/htmx/sync-table?load_all=true` returns all records
2. **Backend unit test:** Default behavior unchanged (paginated)
3. **Manual test:** Walk through TC-001 through TC-005 from spec

## Spec Traceability

| Task | Acceptance Criteria |
|------|-------------------|
| TASK-001 | AC-004, AC-005 |
| TASK-002 | AC-001, AC-008 |
| TASK-003 | AC-002, AC-003, AC-006, AC-009, AC-010 |
| TASK-004 | AC-004, AC-005 |
| TASK-005 | AC-001, AC-008 |
| TASK-006 | AC-007 |
| TASK-007 | AC-004, AC-005 |

## File Change Summary

| File | Action | Reason |
|------|--------|--------|
| `app/main.py` | Modified | Add `load_all` param to HTMX sync-table endpoint |
| `app/templates/index.html` | Modified | Add quick-select buttons, JS logic, update default load |
| `app/templates/partials/sync_table.html` | Modified | Add "Load All" button |
| `app/static/css/styles.css` | Modified | Add pill button and load-all button styles |

## Recommended Execution Order

1. TASK-001 (backend `load_all` param)
2. TASK-002 (button HTML)
3. TASK-005 (CSS styles)
4. TASK-003 (JS logic for quick select)
5. TASK-004 ("Load All" button in table partial)
6. TASK-007 (template data for Load All)
7. TASK-006 (default to 7 days + reset behavior)
8. Manual walkthrough of TC-001 through TC-005

## Plan History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-20 | 1.0.0 | Initial plan from /add:plan |
