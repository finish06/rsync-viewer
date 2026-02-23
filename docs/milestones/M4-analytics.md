# M4 — Analytics & Performance

**Goal:** Add trend analysis, statistics aggregation, data export, and interactive dashboard charts — backed by database and query performance optimizations to handle large datasets
**Status:** IN_PROGRESS
**Appetite:** 2 weeks
**Target Maturity:** beta
**Started:** 2026-02-23
**Completed:** —

## Success Criteria

- [x] Statistics API returns daily/weekly/monthly summaries with per-source breakdowns
- [x] CSV and JSON export endpoints with date range and source filters
- [x] Interactive Chart.js charts on dashboard (duration, file count, bytes over time)
- [x] Customizable date range selector for all analytics views
- [x] Per-source comparison view with side-by-side statistics
- [ ] API response times under 200ms for list operations with 10,000+ records
- [x] Database indexes on all frequently queried columns
- [x] Cursor-based pagination on sync logs endpoint (replaces offset pagination)
- [x] No N+1 query patterns in codebase

## Hill Chart

```
Database Indexing      ████████████████████████████████████  DONE ✅  (cycle-3, c94c34e)
Query Optimization     ████████████████████████████████████  DONE ✅  (cycle-3, c94c34e)
Cursor Pagination      ████████████████████████████████████  DONE ✅  (cycle-3, c94c34e)
Statistics API         ████████████████████████████████████  DONE ✅  (cycle-4, bcb8d52)
Data Export            ████████████████████████████████████  DONE ✅  (cycle-4, bcb8d52)
Dashboard Charts       ████████████████████████████████████  DONE ✅  (cycle-4, bcb8d52)
Redis Caching          ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED (deferred)
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Statistics & Trends | specs/analytics.md | DONE | Summary API, per-source stats, frequency trends (cycle-4, bcb8d52) |
| Data Export | specs/analytics.md | DONE | CSV/JSON export with streaming, filters, pagination (cycle-4, bcb8d52) |
| Dashboard Charts | specs/analytics.md | DONE | Chart.js visualizations, date range picker, source comparison (cycle-4, bcb8d52) |
| Database Indexing | specs/performance.md | DONE | B-tree + composite indexes on query-hot columns (cycle-3, c94c34e) |
| Cursor Pagination | specs/performance.md | DONE | Keyset pagination with offset fallback (cycle-3, c94c34e) |
| Query Optimization | specs/performance.md | DONE | N+1 elimination, lazy file lists, connection pool tuning (cycle-3, c94c34e) |
| Redis Caching | specs/performance.md | SHAPED | Optional cache layer for statistics (deferred if not needed) |

## Dependencies

- M3 must be complete (error handling provides consistent error responses for new endpoints, logging enables performance monitoring)
- Existing SyncLog model and data
- Chart.js already in use for basic charts — extend for trend analysis

## Recommended Implementation Order

1. Database Indexing + Query Optimization (foundation — makes everything else faster)
2. Cursor Pagination (API change, needed before analytics adds more list endpoints)
3. Statistics API + Per-Source Stats (backend endpoints)
4. Data Export (CSV/JSON endpoints, builds on stats queries)
5. Dashboard Charts (frontend, consumes statistics API)
6. Redis Caching (optional, add only if performance targets aren't met without it)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Chart performance with large datasets | Medium | Medium | Server-side aggregation, date range limits, pagination |
| Cursor pagination breaks existing API consumers | Medium | Medium | Keep offset params as deprecated fallback during transition |
| Redis adds infrastructure complexity | Low | Low | Redis is optional — app works without it |
| Export of very large datasets causes timeout | Medium | Medium | Streaming response, enforce max limit, suggest date range |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| cycle-3 | Database Indexing, Query Optimization, Cursor Pagination | COMPLETE | Performance foundations — 25 new tests, 319 total pass. Commit c94c34e |
| cycle-4 | Statistics API, Data Export, Dashboard Charts | COMPLETE | 30 new tests, 349 total pass. All 10 analytics ACs covered. Commit bcb8d52 |

## Retrospective

—
