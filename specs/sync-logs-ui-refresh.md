# Spec: Sync Logs UI Refresh

**Version:** 0.1.0
**Created:** 2026-02-26
**PRD Reference:** docs/prd.md
**Status:** Complete
**Milestone:** M11 — Polish & Infrastructure

## 1. Overview

Update the Sync Logs page to align with the presentation and theming patterns used across the rest of the site. The floating quick-select date buttons are integrated into the filter box (matching the Analytics page pattern), and the page becomes fully responsive down to phone screen sizes with a card-based layout replacing the table on small viewports.

### User Story

As a user, I want the Sync Logs page to have consistent filtering UI and work well on my phone, so that I can monitor sync activity from any device.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Quick-select date range buttons (7d, 30d, Max, Custom) are inside the filter box, not floating above it | Must |
| AC-002 | Selecting "Custom" reveals date picker inputs inline within the filter box | Must |
| AC-003 | Selecting a non-custom range hides the date picker inputs | Must |
| AC-004 | "Last 7 Days" is the default active range on page load | Must |
| AC-005 | All existing filter functionality (source, dry run, empty runs) continues to work | Must |
| AC-006 | On screens below 768px, the sync table switches to a card-per-row layout | Must |
| AC-007 | Each mobile card displays: source name, start time, duration, total size, and a View button | Must |
| AC-008 | Filters stack vertically on screens below 640px | Must |
| AC-009 | Quick-select buttons wrap naturally on narrow viewports | Should |
| AC-010 | Pagination controls remain functional and usable on mobile | Should |
| AC-011 | The filter box visual style matches the Analytics page filter pattern (card with border, consistent padding) | Should |

## 3. User Test Cases

### TC-001: Filter box with integrated date range selection

**Precondition:** User is logged in and on the Sync Logs page.
**Steps:**
1. Observe the filter area
2. Note that quick-select buttons (Last 7 Days, Last 30 Days, Max, Custom) are inside the filter box
3. Click "Last 30 Days"
4. Verify the table reloads with 30-day data
5. Click "Custom"
6. Verify date picker inputs appear inline within the filter box
7. Enter a custom date range and click "Filter"
**Expected Result:** Quick-select and date pickers are all within the same filter card. Data updates correctly for each selection. Date pickers only visible when "Custom" is selected.
**Screenshot Checkpoint:** tests/screenshots/sync-logs-ui-refresh/step-01-filter-box-integrated.png
**Maps to:** TBD

### TC-002: Default state on page load

**Precondition:** User navigates to the Sync Logs page.
**Steps:**
1. Load the page
2. Observe the filter box
**Expected Result:** "Last 7 Days" button is active/highlighted. Table shows last 7 days of data. No date picker inputs visible.
**Screenshot Checkpoint:** tests/screenshots/sync-logs-ui-refresh/step-02-default-state.png
**Maps to:** TBD

### TC-003: Mobile card layout on small screens

**Precondition:** User is on the Sync Logs page on a device below 768px wide (or browser resized).
**Steps:**
1. View the sync logs area
2. Observe that each sync entry is rendered as a card instead of a table row
3. Verify each card shows: source name, start time, duration, total size, and a View button
4. Tap the View button on a card
**Expected Result:** Cards are stacked vertically. Each card is readable without horizontal scrolling. View button opens the sync detail modal.
**Screenshot Checkpoint:** tests/screenshots/sync-logs-ui-refresh/step-03-mobile-cards.png
**Maps to:** TBD

### TC-004: Filters stack on narrow screens

**Precondition:** User is on the Sync Logs page on a device below 640px wide.
**Steps:**
1. Observe the filter box
2. Verify filter controls (source, dry run, empty runs, buttons) stack vertically
3. Verify quick-select buttons wrap to fit
**Expected Result:** All filters are accessible without horizontal scrolling. Inputs are full-width. Quick-select buttons wrap into multiple rows if needed.
**Screenshot Checkpoint:** tests/screenshots/sync-logs-ui-refresh/step-04-filters-stacked.png
**Maps to:** TBD

### TC-005: Existing filter functionality preserved

**Precondition:** User is on the Sync Logs page.
**Steps:**
1. Select a specific source from the dropdown
2. Change "Dry Runs" to "Show"
3. Click "Filter"
4. Click "Reset"
**Expected Result:** Filtering by source, dry run, and empty run works identically to current behavior. Reset returns to default state (Last 7 Days, all sources, dry runs hidden, empty hidden).
**Screenshot Checkpoint:** tests/screenshots/sync-logs-ui-refresh/step-05-filters-working.png
**Maps to:** TBD

## 4. Data Model

No data model changes. This is a purely presentational update.

## 5. API Contract

No API changes. Existing HTMX endpoints remain unchanged:
- `GET /htmx/sync-table` — returns sync table HTML (will now include responsive markup)

## 6. UI Behavior

### Filter Box Layout (Desktop, >= 768px)

```
┌─────────────────────────────────────────────────────────────┐
│  [Last 7 Days] [Last 30 Days] [Max] [Custom]               │
│                                                             │
│  Source: [All Sources ▾]  Dry Runs: [Hide ▾]               │
│  Empty Runs: [Hide ▾]                                       │
│                                                             │
│  (if Custom selected:)                                      │
│  From: [____date____]  To: [____date____]                   │
│                                                             │
│  [Filter]  [Reset]                                          │
└─────────────────────────────────────────────────────────────┘
```

### Filter Box Layout (Mobile, < 640px)

```
┌──────────────────────────┐
│ [7d] [30d] [Max] [Custom]│
│                          │
│ Source:                  │
│ [All Sources          ▾] │
│ Dry Runs:                │
│ [Hide                 ▾] │
│ Empty Runs:              │
│ [Hide                 ▾] │
│                          │
│ (if Custom:)             │
│ From: [__date__]         │
│ To:   [__date__]         │
│                          │
│ [  Filter  ] [  Reset  ] │
└──────────────────────────┘
```

### Sync Card Layout (Mobile, < 768px)

```
┌──────────────────────────┐
│ [source-badge] [DRY RUN] │
│ 2026-02-25 14:30         │
│ Duration: 2m 34s         │
│ Size: 1.2 GB             │
│ Files: 342               │
│               [View]     │
└──────────────────────────┘
```

### States

- **Loading:** Existing loading indicator behavior preserved
- **Empty:** Existing empty state message preserved
- **Error:** No changes
- **Desktop (>= 768px):** Table layout with integrated filter box
- **Tablet (640-768px):** Table with horizontal scroll fallback if needed, filters still row-based
- **Mobile (< 640px):** Card layout, stacked filters

### Screenshot Checkpoints

| Step | Description | Path |
|------|-------------|------|
| 1 | Desktop: filter box with integrated quick-select | tests/screenshots/sync-logs-ui-refresh/step-01-desktop.png |
| 2 | Desktop: custom date range visible | tests/screenshots/sync-logs-ui-refresh/step-02-custom-range.png |
| 3 | Mobile: card layout | tests/screenshots/sync-logs-ui-refresh/step-03-mobile-cards.png |
| 4 | Mobile: stacked filters | tests/screenshots/sync-logs-ui-refresh/step-04-mobile-filters.png |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Window resized from desktop to mobile | Layout switches dynamically via CSS media queries (no reload needed) |
| Very long source name on mobile card | Truncate with ellipsis, full name visible in detail modal |
| Many quick-select buttons on narrow screen | Buttons wrap to second row, no overflow |
| Pagination on mobile | Previous/Next buttons stack or display full-width below cards |
| "Load All" button on mobile | Full-width button, clearly tappable |
| Dry run badge on mobile card | Displayed inline next to source badge |
| Empty state on mobile | Centered message, readable on small screens |

## 8. Dependencies

- No external dependencies
- Changes are limited to:
  - `app/templates/index.html` — restructure filter area, remove floating quick-select
  - `app/templates/partials/sync_table.html` — add responsive card markup alongside table
  - `app/static/css/styles.css` — new responsive styles, media queries, card layout

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-26 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
