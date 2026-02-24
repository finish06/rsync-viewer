# Cycle 5 — M6 Prometheus Metrics & Data Retention

**Milestone:** M6 — Observability
**Maturity:** alpha
**Status:** PLANNED
**Started:** TBD
**Completed:** TBD
**Duration Budget:** 4-8 hours (away mode)

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| Prometheus Metrics | SHAPED | DONE | Agent-1 | ~3 hours | AC-001, AC-002, AC-003, AC-004, AC-009, AC-010 passing |
| Data Retention | SHAPED | DONE | Agent-1 | ~2 hours | AC-007, AC-008 passing |

## Dependencies & Serialization

```
Prometheus Metrics (Agent-1)
    ↓ (sequential, no dependency — just ordering)
Data Retention (Agent-1)
```

Single-threaded execution. Features advance sequentially. Metrics first, then Retention.

## Implementation Plan

### Phase 1: Prometheus Metrics (~3 hours)

**Spec:** `specs/metrics-export.md` AC-001, AC-002, AC-003, AC-004, AC-009, AC-010

**New dependency:** `prometheus-client` in `requirements.txt`

**Implementation approach:**
- New module: `app/metrics.py` — metric definitions and registry
  - Custom sync metrics: `rsync_syncs_total` (Counter), `rsync_sync_duration_seconds` (Histogram), `rsync_files_transferred_total` (Counter), `rsync_bytes_transferred_total` (Counter)
  - API metrics: `rsync_api_requests_total` (Counter), `rsync_api_request_duration_seconds` (Histogram)
  - Health metrics: `rsync_db_connections_active` (Gauge), `rsync_db_connections_pool_size` (Gauge), `rsync_app_info` (Info/Gauge)
- New route: `GET /metrics` in `app/main.py` — returns `generate_latest()` from prometheus-client
  - Unauthenticated (AC-009)
  - Bypass CSRF middleware (standard for Prometheus scraping)
  - Keep rate limiting active
- Middleware: Add `PrometheusMiddleware` to track API request metrics (request count, duration per endpoint/method/status)
- Sync metric recording: Hook into sync log ingestion (POST endpoint) to increment sync counters
- Health metrics: Read from SQLAlchemy engine pool stats

**Config additions (`app/config.py`):**
- `metrics_enabled: bool = True`

**Middleware bypass:**
- Exclude `/metrics` from CSRF middleware path check

**TDD cycle:**
1. RED: Tests for /metrics endpoint, metric names, labels, Prometheus format, CSRF bypass, zero-data case
2. GREEN: Implement metrics module, route, middleware
3. REFACTOR: Extract metric recording into clean functions
4. VERIFY: Full test suite, lint, mypy

### Phase 2: Data Retention (~2 hours)

**Spec:** `specs/metrics-export.md` AC-007, AC-008

**Implementation approach:**
- New module: `app/services/retention.py` — retention cleanup logic
  - `cleanup_old_sync_logs(session, retention_days)` — delete SyncLog records older than N days
  - Handle FK cascade: delete related notification_log entries and file_list entries first (or use cascade)
  - Return count of deleted records
  - Log cleanup activity via structured logging
- Background task: Use FastAPI lifespan context manager
  - On startup, spawn an asyncio background task if `DATA_RETENTION_DAYS > 0`
  - Task sleeps for `RETENTION_CLEANUP_INTERVAL_HOURS`, then runs cleanup
  - Graceful shutdown on app exit

**Config additions (`app/config.py`):**
- `data_retention_days: int = 0` (0 = disabled)
- `retention_cleanup_interval_hours: int = 24`

**New env vars in `.env.example`:**
- `DATA_RETENTION_DAYS=0`
- `RETENTION_CLEANUP_INTERVAL_HOURS=24`
- `METRICS_ENABLED=true`

**TDD cycle:**
1. RED: Tests for cleanup function (deletes old, preserves recent), FK cascade, disabled state, background task scheduling
2. GREEN: Implement retention service and lifespan integration
3. REFACTOR: Clean up, ensure logging is consistent
4. VERIFY: Full test suite, lint, mypy

## Validation Criteria

### Per-Item Validation

- **Prometheus Metrics:** `/metrics` returns valid Prometheus format with all declared metric names. Sync counters increment after log ingestion. API metrics track request counts and durations. Health metrics show DB pool stats and app version. No CSRF required. Minimal overhead (< 5ms).
- **Data Retention:** Cleanup deletes records older than configured days. Related records (notifications, file lists) are cascade-deleted. Disabled when `DATA_RETENTION_DAYS=0`. Background task runs on configured interval. Cleanup count is logged.

### Cycle Success Criteria

- [ ] All features reach DONE position
- [ ] 8 ACs covered: AC-001 through AC-004, AC-007, AC-008, AC-009, AC-010
- [ ] Full test suite passes (350+ tests, 0 failures)
- [ ] Test coverage >= 80%
- [ ] ruff check clean
- [ ] mypy clean
- [ ] No regressions in existing tests

## Agent Autonomy & Checkpoints

**Mode:** High autonomy (Alpha maturity, human away 4-8 hours).

- Agent executes each phase sequentially using TDD
- Agent commits after each completed phase (conventional commits)
- Always run `ruff format` before committing (retro L-012 agreed change)
- Human reviews at cycle completion when they return
- If blocked: agent flags blocker and continues to next phase if possible

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| prometheus-client conflicts with existing deps | Pin version, test import compatibility |
| Metrics middleware adds latency | Benchmark before/after, target < 5ms overhead |
| Retention cascade delete breaks FK constraints | Test with related notification/file records, use proper cascade order |
| Background task doesn't shut down cleanly | Use asyncio.Event for graceful cancellation in lifespan |
| CSRF bypass opens security hole | Only bypass for `/metrics` path, not other unauthenticated routes |

## Notes

- L-007 learning: rate limiting middleware applies to /metrics — this is acceptable (Prometheus retries)
- L-008 learning: CSRF bypass for /metrics needs explicit path exclusion in middleware
- prometheus-client is the standard Python library, widely used, minimal dependencies
- Background retention task pattern is similar to webhook retry scheduling already in codebase
- Grafana dashboards and documentation are deferred to cycle-6
