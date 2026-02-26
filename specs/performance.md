# Spec: Performance Optimization

**Version:** 0.1.0
**Created:** 2026-02-22
**PRD Reference:** docs/prd.md
**Status:** Draft
**Milestone:** M4 — Analytics & Performance

## 1. Overview

Improve application performance through query caching, database indexing, cursor-based pagination, connection pooling tuning, and query optimization to meet the PRD target of < 2s dashboard loads for 1000+ entries.

### User Story

As a homelab administrator with months of sync history, I want the dashboard and API to remain fast and responsive even with thousands of log entries, so that I can quickly check sync status without waiting.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | API response times are under 200ms for common list/detail operations with 10,000+ records | Must |
| AC-002 | Database indexes exist for all frequently queried columns (source_name, created_at, exit_code) | Must |
| AC-003 | Cursor-based pagination replaces offset pagination on the sync logs list endpoint | Must |
| AC-004 | Cursor pagination supports both forward and backward navigation | Must |
| AC-005 | Connection pool size is configurable via environment variable with sensible defaults | Must |
| AC-006 | No N+1 query patterns exist in the codebase | Must |
| ~~AC-007~~ | ~~Redis caching for statistics~~ | ~~Should~~ | **Dropped** — benchmarks show <200ms without caching |
| ~~AC-008~~ | ~~Cache TTL and invalidation~~ | ~~Should~~ | **Dropped** — depends on AC-007 |
| AC-009 | File list data is lazily loaded (not included in list responses, only in detail responses) | Should |
| AC-010 | Query timeout limits prevent runaway queries from blocking the connection pool | Should |

## 3. User Test Cases

### TC-001: Large dataset performance

**Precondition:** Database seeded with 10,000+ sync log entries
**Steps:**
1. Call GET `/api/v1/sync-logs` and measure response time
2. Call GET `/api/v1/sync-logs?source=backup-server` with source filter
3. Navigate to the dashboard and measure page load time
**Expected Result:** All responses return in under 200ms. Dashboard fully renders in under 2 seconds.
**Screenshot Checkpoint:** N/A (performance)
**Maps to:** AC-001

### TC-002: Cursor-based pagination

**Precondition:** Database has 100+ sync log entries
**Steps:**
1. Call GET `/api/v1/sync-logs?limit=20` — note the `next_cursor` in response
2. Call GET `/api/v1/sync-logs?limit=20&cursor={next_cursor}`
3. Call with `direction=backward` to page backwards
**Expected Result:** Each page returns exactly 20 results. Results are consistent even if new data is inserted between requests. No duplicate or missing records across pages.
**Screenshot Checkpoint:** N/A (API)
**Maps to:** AC-003, AC-004

### TC-003: Cache behavior

**Precondition:** Redis is running, caching enabled
**Steps:**
1. Call GET `/api/v1/analytics/summary` — note response time (cache miss)
2. Call the same endpoint again — note response time (cache hit)
3. Submit a new sync log via POST
4. Call the summary endpoint again — verify fresh data
**Expected Result:** Second call is significantly faster (cache hit). After new data submission, cache is invalidated and fresh data is returned.
**Screenshot Checkpoint:** N/A (performance)
**Maps to:** AC-007, AC-008

## 4. Data Model

No new tables. Changes to existing models:

### Index Additions

| Table | Column(s) | Index Type | Rationale |
|-------|-----------|------------|-----------|
| sync_logs | source_name | B-tree | Filter by source |
| sync_logs | created_at | B-tree | Date range queries, ordering |
| sync_logs | exit_code | B-tree | Status filtering |
| sync_logs | (source_name, created_at) | Composite B-tree | Combined filter + sort |
| failure_events | detected_at | B-tree | Date range queries |
| notification_logs | created_at | B-tree | History queries |

## 5. API Contract

### Modified: GET /api/v1/sync-logs

**New Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| cursor | String | No | Opaque cursor for pagination (replaces offset) |
| limit | Integer | No | Page size (default 20, max 100) |
| direction | String | No | `forward` (default) or `backward` |

**Response (200):**
```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6ICIxMjM...",
    "prev_cursor": "eyJpZCI6ICI0NTY...",
    "has_next": true,
    "has_prev": false,
    "limit": 20
  }
}
```

**Note:** The existing `offset`/`page` parameters should be deprecated but kept for backward compatibility during the transition.

### New Headers (on cacheable responses)

| Header | Value | Description |
|--------|-------|-------------|
| Cache-Control | max-age={ttl} | Client-side cache hint |
| X-Cache | HIT or MISS | Whether response was served from Redis cache |

## 6. Configuration

### New Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DB_POOL_SIZE | 10 | SQLAlchemy connection pool size |
| DB_MAX_OVERFLOW | 20 | Max connections beyond pool size |
| DB_POOL_TIMEOUT | 30 | Seconds to wait for a connection |
| QUERY_TIMEOUT_SECONDS | 30 | Max query execution time |
| REDIS_URL | None | Redis connection URL (enables caching when set) |
| CACHE_TTL_SECONDS | 300 | Default cache TTL (5 minutes) |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Redis unavailable | Fall back to uncached responses, log warning, don't error |
| Cursor from different dataset version | Return results from cursor position, no errors |
| Invalid cursor value | Return 400 with clear error message |
| Connection pool exhausted | Queue requests up to timeout, return 503 if timeout exceeded |
| Very large file list in sync log | Lazy load only on detail endpoint, compress in transit |
| Concurrent cache invalidation | Last write wins, stale cache acceptable for TTL window |
| Zero results for query | Return empty data array with null cursors |

## 8. Dependencies

- Redis (optional, for caching — app works without it)
- Existing SyncLog model
- Logging spec (for performance monitoring)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-22 | 0.1.0 | finish06 | Initial spec from TODO conversion |
