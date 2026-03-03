# Implementation Plan: Synthetic Monitoring

**Spec Version**: 0.1.0
**Created**: 2026-03-01
**Team Size**: Solo
**Estimated Duration**: 2-3 days

## Overview

A built-in background task that periodically performs a synthetic transaction — POSTing a canned rsync log to the app's own API, verifying the response, and DELETEing it on success. Failures fire webhooks via the existing dispatch system; Prometheus metrics expose check status and latency.

## Objectives

- Self-monitoring without external tools — the app validates its own ingestion pipeline
- Immediate webhook notification on pipeline breakage
- Observable via Prometheus/Grafana and the admin settings page

## Success Criteria

- All 12 acceptance criteria implemented and tested
- Code coverage >= 80% on new code
- All quality gates passing (ruff, mypy, pytest)
- Follows existing patterns (retention task, HTMX settings, Prometheus metrics)

## Acceptance Criteria Analysis

### AC-001: Background task on configurable interval
- **Complexity**: Medium
- **Effort**: 2h
- **Tasks**: TASK-001, TASK-002
- **Dependencies**: Config settings added first
- **Pattern**: Mirror `retention_background_task()` in `app/services/retention.py`

### AC-002: POST canned log and verify 201
- **Complexity**: Medium
- **Effort**: 2h
- **Tasks**: TASK-003
- **Dependencies**: TASK-001, httpx (already a dependency)
- **Pattern**: Use `httpx.AsyncClient` to POST to self at `http://localhost:{port}/api/v1/sync-logs`

### AC-003: DELETE created log and verify 204
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: TASK-003 (same function)
- **Dependencies**: POST must succeed first
- **Note**: DELETE endpoint requires admin role — use the debug API key which bypasses auth checks when `DEBUG=true`

### AC-004: Webhook on POST failure
- **Complexity**: Medium
- **Effort**: 1h
- **Tasks**: TASK-004
- **Dependencies**: Existing `dispatch_webhooks()` in `app/services/webhook_dispatcher.py`
- **Pattern**: Create transient `FailureEvent` with `failure_type="synthetic_failure"`

### AC-005: Warning on DELETE failure, no webhook
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: TASK-003 (handled inline)

### AC-006: Source name `__synthetic_check` with canned data
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: TASK-003 (constants defined in service module)

### AC-007: Use DEFAULT_API_KEY for auth
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: TASK-003 (read from settings)
- **Note**: `app/api/deps.py:95` — debug key bypass: `if settings.debug and x_api_key == settings.default_api_key`

### AC-008: Prometheus metrics (gauge + histogram)
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: TASK-005
- **Pattern**: Add to `app/metrics.py` alongside existing metrics

### AC-009: Health endpoint includes synthetic status
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: TASK-006
- **Pattern**: Extend `GET /health` in `app/main.py:295`

### AC-010: Settings page section
- **Complexity**: Medium
- **Effort**: 2h
- **Tasks**: TASK-007, TASK-008
- **Pattern**: HTMX partial in `app/routes/settings.py`, template in `app/templates/settings.html`

### AC-011: Graceful shutdown
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: TASK-001 (same shutdown_event pattern as retention task)

### AC-012: Disabled by default, no resource consumption
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: TASK-002 (config gating)

## Implementation Phases

### Phase 0: Configuration (30min)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-001 | Add `synthetic_check_enabled` and `synthetic_check_interval_seconds` to `app/config.py` Settings class | 15min | — | AC-001, AC-012 |
| TASK-002 | Add Prometheus gauge and histogram to `app/metrics.py` | 15min | — | AC-008 |

### Phase 1: Core Service (3h)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-003 | Create `app/services/synthetic_check.py` — canned log data, `run_synthetic_check()` async function (POST, verify, DELETE, record metrics) | 2h | TASK-001, TASK-002 | AC-002, AC-003, AC-005, AC-006, AC-007 |
| TASK-004 | Add webhook dispatch on POST failure — create transient `FailureEvent`, call `dispatch_webhooks()` | 1h | TASK-003 | AC-004 |

### Phase 2: Background Task & Lifespan (1h)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-005 | Create `synthetic_check_background_task()` in same module — async loop mirroring retention pattern, with shutdown_event | 30min | TASK-003 | AC-001, AC-011 |
| TASK-006 | Wire into `app/main.py` lifespan — create_task when enabled, shutdown on exit | 30min | TASK-005 | AC-001, AC-011, AC-012 |

### Phase 3: Health & Settings UI (2h)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-007 | Extend `GET /health` to include `synthetic_check` status from in-memory state | 30min | TASK-005 | AC-009 |
| TASK-008 | Add HTMX routes in `app/routes/settings.py` — GET partial for status display, POST to toggle enable/interval | 1h | TASK-005 | AC-010 |
| TASK-009 | Add template section in `app/templates/settings.html` — status badge, toggle, interval config | 30min | TASK-008 | AC-010 |

### Phase 4: Tests (3h)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-010 | Unit tests for `run_synthetic_check()` — happy path (POST 201, DELETE 204), POST failure, DELETE failure, timeout | 1.5h | TASK-003, TASK-004 | AC-002–AC-007 |
| TASK-011 | Unit tests for background task — interval timing, shutdown, disabled state | 30min | TASK-005 | AC-001, AC-011, AC-012 |
| TASK-012 | Unit tests for health endpoint — enabled/passing, enabled/failing, disabled | 30min | TASK-007 | AC-009 |
| TASK-013 | Unit tests for settings routes — GET partial, POST toggle | 30min | TASK-008 | AC-010 |

### Phase 5: Quality & Polish (30min)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-014 | Run ruff format, ruff check, mypy on all new/modified files | 15min | All tasks | — |
| TASK-015 | Run full test suite, verify coverage >= 80% on new files | 15min | TASK-010–TASK-013 | — |

## Effort Summary

| Phase | Estimated Hours |
|-------|-----------------|
| Phase 0: Configuration | 0.5 |
| Phase 1: Core Service | 3.0 |
| Phase 2: Background Task | 1.0 |
| Phase 3: Health & Settings | 2.0 |
| Phase 4: Tests | 3.0 |
| Phase 5: Quality | 0.5 |
| **Total** | **10.0** |

## Dependencies

### Internal
- Existing webhook dispatch: `app/services/webhook_dispatcher.py` — `dispatch_webhooks(session, event)`
- Existing Prometheus metrics: `app/metrics.py` — custom `registry`
- Existing retention background task pattern: `app/services/retention.py`
- Existing settings HTMX partials: `app/routes/settings.py`
- Existing lifespan wiring: `app/main.py` lifespan function

### External
- `httpx` — already a dependency (used in tests and webhook dispatcher)
- No new pip packages required

## Key Design Decisions

### Self-HTTP vs Direct DB
The synthetic check POSTs via HTTP to the app's own API rather than calling the parser/DB directly. This validates the full stack: routing, auth, parsing, DB write, and DB delete.

### API Key Strategy
Uses `settings.default_api_key` with `DEBUG=true` mode, which bypasses auth checks in `app/api/deps.py:95`. For production where `DEBUG=false`, a dedicated internal API key must be provisioned. The check skips if no valid API key is available.

### In-Memory State
Status (passing/failing/unknown, last_check_at, last_latency_ms, last_error) is held in a module-level dataclass — no DB table needed. Resets on app restart, which is acceptable.

### Minimum Interval
Enforced at 30 seconds to prevent self-DoS. Values below 30 are clamped.

### Webhook Integration
Creates a transient `FailureEvent` (not persisted to DB) with `failure_type="synthetic_failure"` and passes it to `dispatch_webhooks()`. This reuses the existing webhook + Discord formatting pipeline. The `_build_payload()` function in the dispatcher constructs the JSON from the event fields.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Self-request blocked by rate limiter | Medium | Medium | Exclude `__synthetic_check` source or use internal httpx call that bypasses middleware |
| DELETE requires admin role when DEBUG=false | Medium | High | Document API key provisioning; synthetic check logs warning if DELETE returns 403 |
| httpx request to localhost fails in Docker | Low | High | Use `http://127.0.0.1:{port}` or configure base URL; test in Docker |
| Background task leaks on repeated enable/disable | Low | Medium | Track task reference; cancel before starting new one |

## Testing Strategy

1. **Unit Tests** (Phase 4)
   - Mock httpx responses for POST/DELETE
   - Mock `dispatch_webhooks()` to verify webhook firing
   - Mock Prometheus metrics to verify recording
   - Test canned log parsing expectations

2. **Integration** (manual)
   - Run app with `SYNTHETIC_CHECK_ENABLED=true`
   - Verify logs show "Synthetic check passed"
   - Stop DB, verify webhook fires
   - Check `/health` response includes synthetic_check
   - Check `/metrics` includes new gauges

## Deliverables

### Code
| File | Action |
|------|--------|
| `app/config.py` | Modify — add 2 settings |
| `app/metrics.py` | Modify — add gauge + histogram |
| `app/services/synthetic_check.py` | Create — core service + background task |
| `app/main.py` | Modify — wire background task in lifespan, extend /health |
| `app/routes/settings.py` | Modify — add HTMX routes |
| `app/templates/settings.html` | Modify — add settings section |

### Tests
| File | Action |
|------|--------|
| `tests/test_synthetic_check.py` | Create — unit tests for service |
| `tests/test_synthetic_settings.py` | Create — unit tests for settings routes + health |

## Next Steps

1. Review and approve this plan
2. Run `/add:tdd-cycle specs/synthetic-monitoring.md` to execute
