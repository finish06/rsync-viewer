# Implementation Plan: Failure Detection

**Spec Version:** 0.1.0
**Created:** 2026-02-21
**Team Size:** Solo
**Estimated Duration:** 3 days

## Overview

Add failure detection to rsync-viewer: detect failed syncs via non-zero exit codes and stale syncs via configurable frequency monitors with a grace multiplier. Expose via REST API and dashboard UI.

## Objectives

- Detect sync failures (non-zero exit code) at ingestion time
- Detect stale sources (missed expected sync window) via background scheduler
- Provide CRUD API for sync source monitors
- Surface failure/stale status on the dashboard
- Enable downstream notification system (M2 feature: webhook service)

## Success Criteria

- All 11 acceptance criteria implemented and tested
- Code coverage >= 80%
- All quality gates passing (lint, types, tests)
- Backward compatibility with existing sync logs (null exit_code = success)
- Background scheduler runs reliably without crashing the app

## Acceptance Criteria Analysis

### AC-001: Non-zero exit code creates FailureEvent
- **Complexity:** Simple
- **Tasks:** Modify SyncLog model + POST endpoint, create FailureEvent on non-zero exit code
- **Dependencies:** New models must exist first

### AC-002: Configurable sync frequency per source
- **Complexity:** Simple
- **Tasks:** SyncSourceMonitor model + CRUD endpoints
- **Dependencies:** None

### AC-003: Background scheduler checks for stale sources
- **Complexity:** Medium
- **Tasks:** APScheduler setup, stale detection logic, integration with app lifespan
- **Dependencies:** SyncSourceMonitor model, FailureEvent model

### AC-004: Stale sources generate FailureEvent
- **Complexity:** Simple
- **Tasks:** Part of scheduler logic
- **Dependencies:** AC-003

### AC-005: Failure/stale status visible on dashboard
- **Complexity:** Medium
- **Tasks:** Modify sync table template, add badges, query FailureEvents
- **Dependencies:** Models and detection logic complete

### AC-006: Frequency config via dashboard UI
- **Complexity:** Medium
- **Tasks:** New HTMX template, form handling, monitor CRUD via UI
- **Dependencies:** AC-007 (API endpoints)

### AC-007: CRUD API for monitors
- **Complexity:** Medium
- **Tasks:** New router, schemas, endpoints (GET/POST/PUT/DELETE)
- **Dependencies:** SyncSourceMonitor model

### AC-008: GET API for failures
- **Complexity:** Simple
- **Tasks:** New endpoint with query filtering
- **Dependencies:** FailureEvent model

### AC-009: Sources without frequency not checked
- **Complexity:** Simple
- **Tasks:** Scheduler only queries enabled monitors
- **Dependencies:** AC-003

### AC-010: Configurable grace multiplier
- **Complexity:** Simple
- **Tasks:** Field on SyncSourceMonitor, used in stale check calculation
- **Dependencies:** AC-002

### AC-011: Existing logs without exit_code treated as success
- **Complexity:** Simple
- **Tasks:** Nullable field, detection logic checks `exit_code is not None and exit_code != 0`
- **Dependencies:** AC-001

## Implementation Phases

### Phase 1: Data Models & Migrations (~3 hours)

Foundation: new models and schema modifications.

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-001 | Add `exit_code` field to SyncLog model (nullable int) | 30min | — | AC-001, AC-011 |
| TASK-002 | Create SyncSourceMonitor model (SQLModel, table=True) | 45min | — | AC-002, AC-010 |
| TASK-003 | Create FailureEvent model (SQLModel, table=True) | 45min | — | AC-001, AC-004 |
| TASK-004 | Create Pydantic schemas for monitors (Create, Read, List) | 30min | TASK-002 | AC-007 |
| TASK-005 | Create Pydantic schemas for failures (Read, List, filter params) | 30min | TASK-003 | AC-008 |

**Phase Deliverables:**
- `app/models/sync_log.py` — modified (exit_code field)
- `app/models/monitor.py` — new (SyncSourceMonitor)
- `app/models/failure_event.py` — new (FailureEvent)
- `app/schemas/monitor.py` — new
- `app/schemas/failure_event.py` — new

### Phase 2: API Endpoints (~4 hours)

REST API for monitors and failures, plus sync log modification.

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-006 | Modify POST /sync-logs to accept exit_code, create FailureEvent on non-zero | 1h | TASK-001, TASK-003 | AC-001, AC-011 |
| TASK-007 | Create monitors router: GET /api/v1/monitors (list all) | 30min | TASK-002, TASK-004 | AC-007 |
| TASK-008 | POST /api/v1/monitors (create monitor) | 30min | TASK-007 | AC-007 |
| TASK-009 | PUT /api/v1/monitors/{id} (update monitor) | 30min | TASK-007 | AC-007 |
| TASK-010 | DELETE /api/v1/monitors/{id} (delete monitor) | 30min | TASK-007 | AC-007 |
| TASK-011 | Create failures router: GET /api/v1/failures (list with filters) | 45min | TASK-003, TASK-005 | AC-008 |
| TASK-012 | Register new routers in main.py | 15min | TASK-007, TASK-011 | AC-007, AC-008 |

**Phase Deliverables:**
- `app/api/endpoints/monitors.py` — new
- `app/api/endpoints/failures.py` — new
- `app/api/endpoints/sync_logs.py` — modified
- `app/main.py` — modified (router registration)

### Phase 3: Background Scheduler (~3 hours)

Stale sync detection service.

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-013 | Create stale detection service with check logic | 1.5h | TASK-002, TASK-003 | AC-003, AC-004, AC-009, AC-010 |
| TASK-014 | Integrate scheduler into app lifespan (startup/shutdown) | 1h | TASK-013 | AC-003 |
| TASK-015 | Update SyncSourceMonitor.last_sync_at on new sync log ingestion | 30min | TASK-002, TASK-006 | AC-003 |

**Stale detection logic (TASK-013):**
```python
# For each enabled monitor:
# 1. Calculate deadline = last_sync_at + (expected_interval_hours * grace_multiplier)
# 2. If now > deadline AND no existing unresolved stale FailureEvent → create one
# 3. If last_sync_at is None → skip (never synced, no baseline)
```

**Phase Deliverables:**
- `app/services/stale_checker.py` — new
- `app/main.py` — modified (lifespan adds scheduler)
- `app/api/endpoints/sync_logs.py` — modified (update last_sync_at)

### Phase 4: Dashboard UI (~3 hours)

Surface failure status and monitor config on the dashboard.

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-016 | Add failure badges to sync table rows (red "Failed", amber "Stale") | 1h | TASK-003 | AC-005 |
| TASK-017 | Create monitor configuration page/panel (list, add, edit, delete via HTMX) | 1.5h | TASK-007-010 | AC-006 |
| TASK-018 | Add navigation link and stale source indicators to dashboard | 30min | TASK-016, TASK-017 | AC-005, AC-006 |

**Phase Deliverables:**
- `app/templates/` — modified (sync table, new monitor templates)
- `app/main.py` — modified (new HTMX routes for monitors)

### Phase 5: Testing (~4 hours)

Comprehensive test coverage following TDD (tests written first per phase).

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-019 | Unit tests: FailureEvent creation on non-zero exit code | 45min | TASK-006 | AC-001, AC-011 |
| TASK-020 | Unit tests: Monitor CRUD API endpoints | 1h | TASK-007-010 | AC-007 |
| TASK-021 | Unit tests: Failures list endpoint with filters | 30min | TASK-011 | AC-008 |
| TASK-022 | Unit tests: Stale detection logic (within grace, beyond grace, no monitor, disabled) | 1h | TASK-013 | AC-003, AC-004, AC-009, AC-010 |
| TASK-023 | Integration test: Full flow — submit failed sync → FailureEvent created | 30min | TASK-006 | AC-001 |
| TASK-024 | Integration test: Stale detection → FailureEvent, no duplicate stale events | 30min | TASK-013 | AC-003, AC-004 |
| TASK-025 | Test fixtures: sample monitors, failure events, factory fixtures | 30min | TASK-002, TASK-003 | — |

**Phase Deliverables:**
- `tests/unit/test_failure_detection.py` — new
- `tests/unit/test_monitors.py` — new
- `tests/unit/test_stale_checker.py` — new
- `tests/integration/test_failure_flow.py` — new
- `tests/conftest.py` — modified (new fixtures)

### Phase 6: Verification & Polish (~1 hour)

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-026 | Run full quality gates (lint, types, tests, coverage) | 30min | All above | All |
| TASK-027 | Verify spec compliance — every AC has a passing test | 30min | TASK-026 | All |

## Effort Summary

| Phase | Estimated Hours |
|-------|-----------------|
| Phase 1: Data Models | 3h |
| Phase 2: API Endpoints | 4h |
| Phase 3: Background Scheduler | 3h |
| Phase 4: Dashboard UI | 3h |
| Phase 5: Testing | 4h |
| Phase 6: Verification | 1h |
| **Total** | **18h** |

**Note:** Testing runs concurrently with implementation in TDD style (RED → GREEN per phase), not purely sequential. Effective wall-clock time: ~3 days solo.

## Dependencies

### Internal Dependencies
- Existing SyncLog model and POST endpoint (modification)
- Existing API key authentication (reused)
- Existing Jinja2 template patterns (extended)

### External Dependencies
- APScheduler or equivalent (new dependency in requirements.txt)
- No external service dependencies

### Dependency Graph
```
TASK-001 (exit_code field) ──┐
TASK-002 (Monitor model) ───┤
TASK-003 (FailureEvent model)┤
                             ├── TASK-006 (modify POST /sync-logs)
                             ├── TASK-007-010 (monitor CRUD)
                             ├── TASK-011 (failures endpoint)
                             └── TASK-013 (stale checker) ── TASK-014 (scheduler)
                                                           └── TASK-015 (update last_sync_at)

TASK-007-010 ── TASK-017 (monitor UI)
TASK-003 ────── TASK-016 (failure badges)
```

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| APScheduler conflicts with async FastAPI | Medium | High | Use apscheduler's async support or fallback to asyncio.create_task with sleep loop |
| Stale detection duplicate events | Medium | Medium | Check for existing unresolved stale FailureEvent before creating new one |
| Database migration breaks existing data | Low | High | exit_code is nullable, existing rows get NULL (treated as success) |
| Scheduler memory leak on long runs | Low | Medium | Use stateless check function, no accumulated state |
| Grace period edge cases (timezone, DST) | Low | Low | Use UTC throughout, store all datetimes as UTC |

## Testing Strategy

1. **Unit Tests** — Model creation, API endpoint responses, stale detection logic
2. **Integration Tests** — Full flow: submit failed sync → FailureEvent created, stale detection cycle
3. **Edge Cases** — Null exit_code, disabled monitors, duplicate stale events, source without monitor
4. **Quality Gates** — Coverage >= 80%, ruff, mypy, all tests passing

## Deliverables

### Code
- `app/models/monitor.py` — SyncSourceMonitor model
- `app/models/failure_event.py` — FailureEvent model
- `app/schemas/monitor.py` — Monitor schemas
- `app/schemas/failure_event.py` — FailureEvent schemas
- `app/api/endpoints/monitors.py` — Monitor CRUD router
- `app/api/endpoints/failures.py` — Failures list router
- `app/services/stale_checker.py` — Stale detection service

### Modified
- `app/models/sync_log.py` — exit_code field
- `app/api/endpoints/sync_logs.py` — exit_code handling, last_sync_at update
- `app/main.py` — router registration, scheduler lifespan
- `app/templates/` — failure badges, monitor config UI
- `tests/conftest.py` — new fixtures
- `requirements.txt` — APScheduler dependency

### Tests
- `tests/unit/test_failure_detection.py`
- `tests/unit/test_monitors.py`
- `tests/unit/test_stale_checker.py`
- `tests/integration/test_failure_flow.py`

## Next Steps

1. Review and approve this plan
2. Run `/add:tdd-cycle specs/failure-detection.md` to execute
3. Each phase follows RED → GREEN → REFACTOR
4. Verify with `/add:verify` after completion

## Plan History

- 2026-02-21: Initial plan created from spec v0.1.0
