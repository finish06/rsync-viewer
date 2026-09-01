# Spec: CSV export from the UI

## 1. Overview

`GET /api/v1/analytics/export` already renders CSV/JSON, but it is reachable
only by hand-crafting a URL and it filters by a **single** source. Give the
Transfers page an export control with the filters an operator actually wants:
all sources, a chosen subset, exclude/include the synthetic probe, and a date
range.

### User Story
As an operator I want to export my sync history to CSV — everything, or just
the sources and dates I care about, without the synthetic probe noise — so I
can chart it elsewhere or hand it to someone.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | `GET /api/v1/analytics/export` accepts **repeated** `source` parameters (`?source=a&source=b`) and returns rows for any of them; a single `source=a` behaves exactly as before; no `source` means all sources. | Must |
| AC-002 | The existing `synthetic` filter (`hide` default / `only` / `show`) keeps working with multi-source selection: `hide` excludes the probe even when it is one of the selected sources. | Must |
| AC-003 | `start` / `end` date filters are unchanged and combine with the above; `MAX_EXPORT_LIMIT` still caps the row count and the response says so (see AC-007). | Must |
| AC-004 | The Transfers page has an **Export** button that opens a panel with: source selection (a checkbox list of known sources plus an "All sources" default), an "include synthetic checks" toggle (off by default), a date range (prefilled from the page's current filters, editable), and a format choice (CSV default, JSON available). | Must |
| AC-005 | Submitting downloads the file through the browser (cookie-authenticated GET), naming it `rsync-export-YYYYMMDD.csv` / `.json`; the panel closes and no page navigation occurs. | Must |
| AC-006 | The panel's request URL reflects the choices exactly: one `source` parameter per selected source (none when "all"), `synthetic=hide|show`, `start`/`end` when set, `format`. | Must |
| AC-007 | The panel states the export cap ("up to 10,000 rows, newest first") so a truncated export is never a surprise. | Should |
| AC-008 | Viewer role can export (existing endpoint permission is unchanged). | Must |

## 3. User Test Cases
- **TC-001** Export with defaults → CSV of all sources, no synthetic rows, current date range; file downloads with the dated name.
- **TC-002** Select two of three sources, tick "include synthetic checks", set a custom range → the request carries both `source` params, `synthetic=show`, and both dates.
- **TC-003** Deselect every source → the export button is disabled with a hint (never silently exports everything).
- **TC-004** A source named with regex/CSV-hostile characters exports intact (values are quoted by the csv writer).

## 4. API Contract
```
GET /api/v1/analytics/export?format=csv&source=movies&source=tv&synthetic=hide&start=2026-08-01&end=2026-08-31
→ 200 text/csv, attachment; filename=sync_export.csv
```
Unchanged columns: source_name, start_time, end_time, duration_seconds,
file_count, bytes_received, bytes_sent, total_size_bytes, exit_code, status,
is_dry_run.

## 5. Edge Cases
- `source` repeated with an unknown name → no rows for it (no error).
- `synthetic=only` ignores `source` (existing behaviour, kept).
- Empty result → header-only CSV, still downloads.
- Very long source lists → URL length is bounded by the number of real sources; no batching needed.

## 6. Screenshot Checkpoints
`tests/screenshots/csv-export/step-01-export-panel.png`.
