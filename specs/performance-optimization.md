# Performance Optimization — Blocking Async & Query Efficiency

**Status:** In Progress
**Milestone:** M-GA (GA Maintenance)
**Priority:** High
**Dependencies:** None (all optimizations target existing code)

## Feature Description

Fix performance bottlenecks identified via code profiling: blocking bcrypt operations on the async event loop, oversized query result sets loading unnecessary data, and missing database indexes. These optimizations improve request throughput and memory efficiency without changing user-facing behavior.

## User Story

As a **homelab operator running rsync-viewer**, I want the application to handle concurrent requests efficiently so that the dashboard remains responsive while sync logs are being ingested.

## Acceptance Criteria

### Blocking Async Fixes
- **AC-001:** `verify_password()` in login handler (`app/routes/auth.py`) runs in a thread pool executor, not on the event loop
- **AC-002:** `verify_password()` in API auth login (`app/api/endpoints/auth.py`) runs in a thread pool executor
- **AC-003:** Existing login tests still pass (no behavior change)

### Query Optimization
- **AC-010:** Sync log list endpoints exclude `raw_content` and `file_list` from SELECT (summary queries only)
- **AC-011:** Sync log detail endpoint still returns full `raw_content` and `file_list`
- **AC-012:** Dashboard sync table loads without `raw_content` (reduced memory footprint)
- **AC-013:** API `GET /api/v1/sync-logs` list response excludes `raw_content` (use summary schema)
- **AC-014:** API `GET /api/v1/sync-logs/{id}` detail response includes full `raw_content`

### Database Indexes
- **AC-020:** Composite index on `api_keys(is_active, key_prefix)` for fast key lookups
- **AC-021:** Composite index on `notification_logs(status, created_at)` for filtered pagination
- **AC-022:** All existing tests pass after index additions

## Edge Cases

- Login with incorrect password must still show proper error (not executor crash)
- Sync log list with zero results returns empty list (not error from missing fields)
- API consumers relying on `raw_content` in list responses must use the detail endpoint instead

## Backlog (Deferred)

- Notification log query restructure (joins before pagination) — complex refactor, lower ROI
- Admin user list query caching — low impact with < 1000 users
- WebhookOptions FK index verification — low impact with < 100 webhooks
