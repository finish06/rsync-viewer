# Cycle 4 — M4 Analytics Features

**Milestone:** M4 — Analytics & Performance
**Maturity:** alpha
**Status:** PLANNED
**Started:** TBD
**Completed:** TBD
**Duration Budget:** 4-6 hours (away mode)

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| Statistics API | SHAPED | DONE | Agent-1 | ~2 hours | AC-001, AC-002, AC-003 passing |
| Data Export | SHAPED | DONE | Agent-1 | ~1.5 hours | AC-004, AC-005, AC-010 passing |
| Dashboard Charts | SHAPED | DONE | Agent-1 | ~2.5 hours | AC-006, AC-007, AC-008, AC-009 passing |

## Dependencies & Serialization

```
Statistics API (Agent-1)
    ↓ (Export reuses aggregation query patterns from Stats)
Data Export (Agent-1)
    ↓ (Charts consume the Statistics API endpoints)
Dashboard Charts (Agent-1)
```

Single-threaded execution. Features advance sequentially.

## Implementation Plan

### Phase 1: Statistics API (~2 hours)

**Spec:** `specs/analytics.md` AC-001, AC-002, AC-003

**Endpoints to build:**
- `GET /api/v1/analytics/summary` — daily/weekly/monthly aggregation with date range + source filter
- `GET /api/v1/analytics/sources` — per-source aggregate stats (total syncs, success rate, avg duration, avg files, avg bytes, last_sync_at)

**Implementation approach:**
- New router: `app/api/endpoints/analytics.py`
- New schemas: `app/schemas/analytics.py` (SummaryPeriod, SummaryDataPoint, SourceStats, etc.)
- SQLAlchemy aggregate queries on SyncLog — GROUP BY date_trunc + source_name
- Frequency trend data as time series (syncs per day/week for a source)

TDD cycle:
1. RED: Write tests asserting endpoint responses match spec contract
2. GREEN: Implement aggregation queries and endpoint handlers
3. REFACTOR: Extract shared query builders if patterns emerge
4. VERIFY: Full test suite, lint, mypy

### Phase 2: Data Export (~1.5 hours)

**Spec:** `specs/analytics.md` AC-004, AC-005, AC-010

**Endpoints to build:**
- `GET /api/v1/analytics/export?format=csv` — CSV download with date range + source filter
- `GET /api/v1/analytics/export?format=json` — JSON download with same filters

**Implementation approach:**
- Add to existing `app/api/endpoints/analytics.py` router
- CSV: Use `StreamingResponse` with `csv.writer` for memory efficiency
- JSON: Use `StreamingResponse` for large datasets
- Enforce max limit (default 10000) with pagination support (offset param)
- Set proper Content-Disposition headers for file download

TDD cycle:
1. RED: Write tests for CSV/JSON format, filtering, pagination, max limit
2. GREEN: Implement export endpoint with streaming
3. REFACTOR: Share query building logic with statistics endpoints
4. VERIFY: Full test suite, lint, mypy

### Phase 3: Dashboard Charts (~2.5 hours)

**Spec:** `specs/analytics.md` AC-006, AC-007, AC-008, AC-009

**UI approach:**
- New route: `GET /analytics` — dedicated analytics page
- New template: `app/templates/analytics.html`
- HTMX partials for chart data loading
- Chart.js line chart (duration over time), bar chart (file counts), area chart (bytes transferred)
- Date range picker (start/end date inputs)
- Source filter dropdown
- Period selector (daily/weekly/monthly)
- Per-source comparison view (AC-008) — side-by-side stats cards
- Success/failure rate chart (AC-009) — stacked bar or line chart

**Implementation approach:**
- Charts load data from `/api/v1/analytics/summary` via HTMX/fetch
- Date range picker triggers HTMX requests to reload chart partials
- Chart.js configured inline (same pattern as existing charts)
- Navigation link added to sidebar/header

TDD cycle:
1. RED: Write tests for new route, template rendering, HTMX partial responses
2. GREEN: Implement templates, route handlers, Chart.js integration
3. REFACTOR: Extract chart configuration patterns
4. VERIFY: Full test suite, lint, mypy

## Validation Criteria

### Per-Item Validation

- **Statistics API:** Endpoints return correct aggregations for daily/weekly/monthly periods. Per-source stats include success rate and averages. Empty date ranges return empty data arrays.
- **Data Export:** CSV has correct headers and row data. JSON format matches spec. Pagination with limit/offset works. Max limit enforced. Streaming works for large exports.
- **Dashboard Charts:** Analytics page renders with Chart.js. Date range picker updates charts. Source filter works. Per-source comparison shows side-by-side. Charts handle empty data gracefully.

### Cycle Success Criteria

- [ ] All 3 features reach DONE position
- [ ] Analytics spec ACs covered: AC-001 through AC-010 (10 total)
- [ ] Full test suite passes (no regressions on existing 319+ tests)
- [ ] Test coverage >= 80%
- [ ] ruff check clean
- [ ] mypy clean
- [ ] New /analytics route accessible and functional

### Out of Scope

- AC-007 Redis caching (deferred per milestone plan)
- Pre-aggregated DailyStats table (only if query performance is insufficient)
- E2E/screenshot tests (alpha maturity — not required)

## Agent Autonomy & Checkpoints

**Mode:** High autonomy (Alpha maturity, human away 4+ hours).

- Agent executes each phase sequentially using TDD
- Agent commits after each completed phase (conventional commits)
- Human reviews at cycle completion when they return
- If blocked: agent flags blocker and continues to next phase if possible

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Chart.js CDN unavailable during testing | Use existing Chart.js setup already in project |
| Large dataset aggregation slow | Indexes from cycle-3 already in place; date range limits enforce bounded queries |
| Export streaming fails for very large datasets | Enforce max limit (10000), suggest narrower date range in error message |
| Template complexity for analytics page | Follow existing HTMX patterns in main.py; keep initial charts simple |
| Missing duration/bytes on old sync records | Use COALESCE/NULL handling in aggregation queries; exclude NULLs from averages |

## Notes

- Performance infrastructure from cycle-3 (indexes, connection pool, cursor pagination) supports this cycle's workload.
- Analytics page is a NEW route (`/analytics`), keeping the main dashboard clean.
- Chart.js is already available in the project — extend existing patterns.
- L-002 learning: Jinja2 filter pattern may be useful for formatting stat values in templates.
- L-007 learning: slowapi rate limits apply to new endpoints too — use default limits.
- L-008 learning: CSRF middleware will need tokens on any form submissions in the analytics page.
