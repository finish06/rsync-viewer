# M4 — Analytics & Performance

**Goal:** Add trend analysis, statistics aggregation, data export, and interactive dashboard charts — backed by database and query performance optimizations to handle large datasets
**Status:** IN_PROGRESS
**Appetite:** 2 weeks
**Target Maturity:** beta
**Started:** 2026-02-23
**Completed:** —

## Success Criteria

- [ ] Statistics API returns daily/weekly/monthly summaries with per-source breakdowns
- [ ] CSV and JSON export endpoints with date range and source filters
- [ ] Interactive Chart.js charts on dashboard (duration, file count, bytes over time)
- [ ] Customizable date range selector for all analytics views
- [ ] Per-source comparison view with side-by-side statistics
- [ ] API response times under 200ms for list operations with 10,000+ records
- [ ] Database indexes on all frequently queried columns
- [ ] Cursor-based pagination on sync logs endpoint (replaces offset pagination)
- [ ] No N+1 query patterns in codebase

## Hill Chart

```
Statistics API         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Data Export            ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Dashboard Charts       ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Performance Tuning     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Statistics & Trends | specs/analytics.md | SHAPED | Summary API, per-source stats, frequency trends |
| Data Export | specs/analytics.md | SHAPED | CSV/JSON export with filters |
| Dashboard Charts | specs/analytics.md | SHAPED | Chart.js visualizations, date range picker, source comparison |
| Database Indexing | specs/performance.md | SHAPED | B-tree indexes on query-hot columns |
| Cursor Pagination | specs/performance.md | SHAPED | Replace offset pagination, forward/backward support |
| Query Optimization | specs/performance.md | SHAPED | N+1 elimination, lazy loading file lists, connection pool tuning |
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
| cycle-3 | Database Indexing, Query Optimization, Cursor Pagination | PLANNED | Performance foundations — indexes, N+1 fixes, keyset pagination |
| cycle-4 | Statistics API, Data Export, Dashboard Charts | — | User-facing analytics (planned after cycle-3) |

## Retrospective

—
