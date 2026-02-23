# Cycle 3 — M4 Performance Foundations

**Milestone:** M4 — Analytics & Performance
**Maturity:** alpha
**Status:** COMPLETE
**Started:** 2026-02-23
**Completed:** 2026-02-23
**Duration Budget:** 2-4 hours (away mode)

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| Database Indexing | SHAPED | DONE | Agent-1 | ~1 hour | AC-002 passing, composite indexes on hot columns |
| Query Optimization | SHAPED | DONE | Agent-1 | ~1.5 hours | AC-006, AC-009 passing, no N+1 patterns, lazy file lists |
| Cursor Pagination | SHAPED | DONE | Agent-1 | ~2 hours | AC-003, AC-004 passing, offset fallback kept for backward compat |

## Dependencies & Serialization

```
Database Indexing (Agent-1)
    ↓ (Query optimization benefits from indexes being in place)
Query Optimization (Agent-1)
    ↓ (Cursor pagination changes the API response shape, build on optimized queries)
Cursor Pagination (Agent-1)
```

Single-threaded execution. Features advance sequentially.

## Implementation Plan

### Phase 1: Database Indexing (~1 hour)

**Spec:** `specs/performance.md` AC-002

**Current state:**
- Individual indexes exist: `source_name`, `start_time`, `is_dry_run` on SyncLog
- Individual indexes exist on FailureEvent: `source_name`, `failure_type`, `detected_at`
- WebhookEndpoint has `enabled` index
- NotificationLog has FK indexes but no `created_at` index
- **No composite indexes anywhere**

TDD cycle:
1. RED: Write tests asserting composite indexes exist on the database tables
2. GREEN: Add composite indexes to models:
   - SyncLog: `(source_name, created_at)` — combined filter + sort (most common query pattern)
   - SyncLog: `exit_code` — status filtering (missing per spec)
   - SyncLog: `created_at` — date range queries (start_time exists but created_at is used for ordering)
   - FailureEvent: `(source_name, detected_at)` — failure filtering by source + time
   - NotificationLog: `created_at` — notification history ordering
3. REFACTOR: Verify index names follow consistent convention
4. VERIFY: Full test suite, lint, mypy

**Key notes:**
- Use `__table_args__` with `Index()` for composite indexes
- Keep existing individual indexes (no regression)
- Connection pool config (AC-005): Add `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT` settings

### Phase 2: Query Optimization (~1.5 hours)

**Spec:** `specs/performance.md` AC-006, AC-009, AC-010

**Current state:**
- Webhook/notification batch loading is already optimized (good pattern)
- API key verification loads ALL active keys per request (N+1 risk)
- File list data is included in list responses (should be lazy loaded)
- No query timeout configured

TDD cycle:
1. RED: Write tests for:
   - File list NOT included in list endpoint response (AC-009)
   - File list IS included in detail endpoint response
   - Query timeout setting exists and is configurable (AC-010)
   - API key lookup is efficient (no loading all keys)
2. GREEN: Implement:
   - Exclude `file_list` from SyncLog list serialization (use a `SyncLogListResponse` schema without file_list)
   - Add query timeout to connection pool config
   - Optimize API key lookup (prefix-based lookup if feasible, otherwise acceptable as-is for homelab scale)
3. REFACTOR: Clean up response schemas
4. VERIFY: Full test suite, lint, mypy

### Phase 3: Cursor Pagination (~2 hours)

**Spec:** `specs/performance.md` AC-003, AC-004

**Current state:**
- Offset/limit pagination on `GET /api/v1/sync-logs` (lines 131-175 of sync_logs.py)
- HTMX table also uses offset/limit (main.py lines 270-343)

TDD cycle:
1. RED: Write tests for:
   - `cursor` param returns keyset-paginated results (AC-003)
   - `direction=backward` paginates in reverse (AC-004)
   - Response includes `pagination` object with `next_cursor`, `prev_cursor`, `has_next`, `has_prev`
   - `offset`/`limit` params still work as deprecated fallback
   - Invalid cursor returns 400
   - Empty result set returns null cursors
2. GREEN: Implement:
   - Base64-encoded cursor containing `(id, start_time)` for stable ordering
   - Keyset WHERE clause: `WHERE (start_time, id) < (:cursor_time, :cursor_id)` for forward
   - Keep existing offset params working (deprecated but functional)
   - Update response schema with `pagination` envelope
3. REFACTOR: Extract cursor encoding/decoding to a utility
4. VERIFY: Full test suite, lint, mypy

**Decision:** Offset pagination kept as deprecated fallback per user preference. Both cursor and offset work — cursor is default when no offset/page params provided.

## Validation Criteria

### Per-Item Validation

- **Database Indexing:** Composite indexes verified in DB schema. Connection pool configurable via env vars.
- **Query Optimization:** No N+1 patterns. File list lazy-loaded on detail only. Query timeout configurable.
- **Cursor Pagination:** Forward + backward cursor navigation works. Offset fallback preserved. Response uses pagination envelope.

### Cycle Success Criteria

- [ ] All 3 features reach DONE position
- [ ] Performance spec ACs covered: AC-002, AC-003, AC-004, AC-005, AC-006, AC-009, AC-010 (7 of 10)
- [ ] Full test suite passes (no regressions on existing 294 tests)
- [ ] Test coverage >= 80%
- [ ] ruff check clean
- [ ] mypy clean
- [ ] API response time under 500ms for list ops (relaxed from spec's 200ms)

### Out of Scope (deferred to later cycles)

- AC-001: Response time benchmarking with 10k+ records (need seeded test data)
- AC-007: Redis caching (optional, deferred per milestone plan)
- AC-008: Cache TTL and invalidation (depends on Redis)
- Statistics API, Data Export, Dashboard Charts (M4 cycle-4)

## Agent Autonomy & Checkpoints

**Mode:** High autonomy (Alpha maturity, human away 2-4 hours).

- Agent executes each phase sequentially using TDD
- Agent commits after each completed phase (conventional commits)
- Human reviews at cycle completion when they return
- If blocked: agent flags blocker and continues to next phase if possible

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Cursor pagination breaks existing API consumers | Keep offset params as deprecated fallback. Both work simultaneously. |
| Composite indexes slow down writes | Homelab scale — write overhead is negligible with <100 writes/day |
| API key lookup optimization scope creep | Keep current bcrypt-loop approach if <10 keys. Only optimize if measurably slow. |
| Schema changes break existing tests | Run full test suite after each phase. Fix regressions immediately. |

## Notes

- Performance target relaxed to 500ms (from spec's 200ms) per user preference for homelab hardware.
- Redis caching (AC-007, AC-008) intentionally deferred — only add if performance targets not met without it.
- This cycle covers the "infrastructure" half of M4. A follow-up cycle-4 will cover Statistics API, Data Export, and Dashboard Charts.
- L-007 learning: slowapi rate limiting headers need explicit `headers_enabled=True` — same pattern may apply to new middleware.
- L-008 learning: middleware changes may require updating test fixtures (e.g., CSRF tokens broke tests in cycle-2).
