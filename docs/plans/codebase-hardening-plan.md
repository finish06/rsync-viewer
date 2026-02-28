# Implementation Plan: Codebase Hardening & Optimization

**Spec Version**: codebase-hardening.md v0.1.0
**Created**: 2026-02-28
**Team Size**: Solo
**Estimated Duration**: 3–4 days

## Overview

Break up the 2,163-line `app/main.py` into focused route modules, remove dead code, eliminate duplication, fix CSRF gaps, centralize business logic, and raise test coverage from 83% to 90%+. Zero regressions allowed — all existing tests must pass throughout.

## Objectives

- Reduce `app/main.py` from 2,163 lines to ~200 lines (app factory + middleware + router includes)
- Eliminate all duplicated business logic (registration, filters, JWT decode, test payloads)
- Expand CSRF protection to all state-mutating HTMX routes
- Raise test coverage to 90%+ with security and edge case tests
- Zero breaking changes to API or UI behavior

## Success Criteria

- [ ] All 18 acceptance criteria implemented
- [ ] All existing 596+ tests pass (zero regressions)
- [ ] New tests bring total coverage to 90%+
- [ ] All quality gates passing (ruff, mypy, pytest)
- [ ] No route paths changed — only internal file organization

## Implementation Phases

### Phase 1: Quick Wins — Dead Code & Fixes (1–2 hours)

Low-risk changes that can be verified immediately. Each is an independent commit.

| Task ID | Description | ACs | Effort | Dependencies |
|---------|-------------|-----|--------|--------------|
| T-01 | Remove `has_permission()` and `PERMISSIONS` dict from `auth.py`; remove orphaned tests | AC-004 | 15min | None |
| T-02 | Replace hardcoded `"1.5.0"` in `set_app_info()` and `FastAPI(version=)` with `settings.app_version` | AC-005 | 10min | None |
| T-03 | Move `RedirectResponse` imports to module level in `main.py` | AC-012 | 10min | None |
| T-04 | Remove 27 redundant in-function imports in `main.py` | AC-003 | 20min | None |
| T-05 | Expand `CSRF_PROTECTED_PREFIXES` to cover all `/htmx/` state-mutating routes | AC-006 | 15min | None |

**Phase Duration**: 1–2 hours
**Risk**: Low — each change is small and independently testable
**Verify**: Run full test suite after each commit

### Phase 2: Extract Shared Services (2–3 hours)

Create service functions to eliminate duplicated logic. These must land before the route split so that the new route modules can import them.

| Task ID | Description | ACs | Effort | Dependencies |
|---------|-------------|-----|--------|--------------|
| T-06 | Extract `_apply_sync_filters(statement, source, start, end, dry_run, hide_empty)` helper | AC-007 | 30min | None |
| T-07 | Extract `register_user()` service function; wire into both HTMX route and API endpoint | AC-008 | 45min | None |
| T-08 | Extract `build_test_webhook_payload()` service function; wire into both HTMX and API | AC-009 | 30min | None |
| T-09 | Consolidate JWT decode in `deps.py` and `middleware.py` to use `decode_token()` from `auth.py` | AC-010 | 30min | None |
| T-10 | Consolidate duplicate bcrypt API key lookup logic in `deps.py` | AC-018 | 30min | None |

**Phase Duration**: 2–3 hours
**Risk**: Medium — changing auth/JWT paths requires careful testing
**Verify**: Run full test suite after each extraction. Spot-check auth flows manually.

### Phase 3: Route Module Split (3–4 hours)

The main event. Break `app/main.py` into domain-specific route modules. This is a mechanical refactoring — move handlers into new files, convert to `APIRouter`, update imports.

| Task ID | Description | ACs | Effort | Dependencies |
|---------|-------------|-----|--------|--------------|
| T-11 | Create `app/routes/` package with `__init__.py` | AC-001 | 5min | None |
| T-12 | Extract `app/routes/pages.py` — index, analytics redirect, login/register page renders, settings page | AC-001, AC-002 | 30min | T-11 |
| T-13 | Extract `app/routes/auth.py` — login POST, logout, OIDC login/callback, forgot/reset password | AC-001, AC-002, AC-011 | 45min | T-11, T-07 |
| T-14 | Extract `app/routes/dashboard.py` — sync table, charts, detail modal, notifications tab | AC-001, AC-002 | 30min | T-11, T-06 |
| T-15 | Extract `app/routes/settings.py` — SMTP GET/POST/test, OIDC GET/POST/test-discovery | AC-001, AC-002 | 30min | T-11 |
| T-16 | Extract `app/routes/api_keys.py` — list, add form, create, revoke | AC-001, AC-002, AC-011 | 20min | T-11 |
| T-17 | Extract `app/routes/webhooks.py` — full CRUD, toggle, test | AC-001, AC-002, AC-011 | 30min | T-11, T-08 |
| T-18 | Extract `app/routes/admin.py` — user management (list, role change, toggle, delete) | AC-001, AC-002, AC-011 | 20min | T-11 |
| T-19 | Wire all routers into `main.py`; convert admin guards to shared dependency | AC-002, AC-011 | 30min | T-12 through T-18 |
| T-20 | Update test patch targets from `app.main` to new module paths | AC-017 | 30min | T-19 |

**Phase Duration**: 3–4 hours
**Risk**: High — this touches every route. Test suite is the safety net.
**Verify**: Run full test suite after T-19. Fix any broken patches in T-20. Re-run.

### Phase 4: Test Hardening (3–4 hours)

Write new tests targeting gaps identified in the audit. Focus on security, edge cases, and untested routes.

| Task ID | Description | ACs | Effort | Dependencies |
|---------|-------------|-----|--------|--------------|
| T-21 | CSRF enforcement tests: POST/PUT/DELETE to all HTMX routes without token → 403 | AC-015 | 45min | T-05 |
| T-22 | Auth bypass tests: admin endpoints accessed by viewer/operator/anon → 403 | AC-015 | 30min | T-18 |
| T-23 | Registration consistency tests: same validation from UI and API | AC-014, AC-015 | 30min | T-07 |
| T-24 | Tests for untested routes: `/htmx/api-keys/add`, `/htmx/webhooks/{id}/edit` | AC-014 | 30min | T-16, T-17 |
| T-25 | Edge case tests: malformed rsync output, expired JWT, empty DB states | AC-016 | 45min | Phase 3 |
| T-26 | Tests for extracted services: `_apply_sync_filters`, `register_user`, `build_test_webhook_payload` | AC-014 | 30min | Phase 2 |
| T-27 | Coverage gap analysis: run `--cov-report=html`, identify remaining <90% modules, write targeted tests | AC-013 | 1h | T-21 through T-26 |

**Phase Duration**: 3–4 hours
**Risk**: Low — adding tests can't break existing functionality
**Verify**: `pytest --cov=app --cov-fail-under=90` passes

### Phase 5: Final Verification (30 min)

| Task ID | Description | ACs | Effort | Dependencies |
|---------|-------------|-----|--------|--------------|
| T-28 | Run full quality gates: ruff check, ruff format, mypy, pytest --cov | AC-017 | 15min | All |
| T-29 | Verify `app/main.py` is under 250 lines | AC-001, AC-002 | 5min | T-19 |
| T-30 | Spot-check: start app, navigate all pages, submit a sync log | AC-017 | 10min | All |

**Phase Duration**: 30 minutes

## Effort Summary

| Phase | Estimated Hours | Description |
|-------|-----------------|-------------|
| Phase 1: Quick Wins | 1.5h | Dead code, imports, CSRF, version fix |
| Phase 2: Extract Services | 2.5h | Shared filters, registration, JWT, payloads |
| Phase 3: Route Split | 3.5h | 7 route modules + wiring + test patches |
| Phase 4: Test Hardening | 3.5h | Security, edge cases, coverage to 90% |
| Phase 5: Verification | 0.5h | Quality gates, smoke test |
| **Total** | **11.5h** | **~2 days at focused pace** |
| **With contingency (20%)** | **~14h** | **~3 days** |

## Dependency Graph

```
Phase 1 (T-01 through T-05) — independent, any order
    ↓
Phase 2 (T-06 through T-10) — independent of each other, all before Phase 3
    ↓
Phase 3 (T-11 first, then T-12–T-18 in any order, then T-19, then T-20)
    ↓
Phase 4 (T-21 through T-27) — mostly independent, T-27 last
    ↓
Phase 5 (T-28 through T-30) — sequential
```

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Route split breaks test patch targets | High | Medium | T-20 dedicated to fixing patches; run suite after each module extraction |
| CSRF expansion breaks legitimate HTMX requests | Medium | High | Ensure all HTMX forms include CSRF token; test each route before committing |
| Service extraction changes subtle behavior | Medium | Medium | Existing tests are the safety net; run after each extraction |
| Coverage target (90%) not reachable | Low | Low | 83% → 90% is 7 points; audit found clear gaps to fill |
| Circular imports from route modules | Low | Medium | Route modules only import services and deps, never each other |

## Testing Strategy

1. **Regression tests**: Existing 596+ tests run after every phase
2. **Security tests** (Phase 4): CSRF enforcement, auth bypass, input injection
3. **Edge case tests** (Phase 4): Malformed input, expired tokens, empty states
4. **Integration tests** (Phase 4): Registration consistency across UI/API paths
5. **Coverage gate**: `pytest --cov=app --cov-fail-under=90` in Phase 5

## Deliverables

### New Files
- `app/routes/__init__.py`
- `app/routes/pages.py`
- `app/routes/auth.py`
- `app/routes/dashboard.py`
- `app/routes/settings.py`
- `app/routes/api_keys.py`
- `app/routes/webhooks.py`
- `app/routes/admin.py`
- `app/services/registration.py`
- `app/services/sync_filters.py`

### Modified Files
- `app/main.py` (reduced from 2,163 to ~200 lines)
- `app/services/auth.py` (dead code removed)
- `app/api/deps.py` (JWT/bcrypt consolidation)
- `app/middleware.py` (CSRF prefixes expanded, JWT consolidated)
- `app/api/endpoints/auth.py` (uses registration service)
- `app/api/endpoints/webhooks.py` (uses test payload service)
- Multiple test files (patch target updates)

### New Test Files
- `tests/test_csrf_enforcement.py`
- `tests/test_auth_bypass.py`
- `tests/test_registration_consistency.py`
- `tests/test_edge_cases.py`
- `tests/test_extracted_services.py`

## Commit Strategy

One commit per task or small group of related tasks. Conventional commit format:

- `refactor: remove dead has_permission() code` (T-01)
- `fix: use settings.app_version for FastAPI and Prometheus version` (T-02)
- `refactor: clean up redundant imports in main.py` (T-03, T-04)
- `fix: expand CSRF protection to all HTMX mutations` (T-05)
- `refactor: extract sync filter helper` (T-06)
- `refactor: extract registration service` (T-07)
- `refactor: extract webhook test payload service` (T-08)
- `refactor: consolidate JWT decode calls` (T-09)
- `refactor: consolidate API key bcrypt lookup` (T-10)
- `refactor: split main.py into route modules` (T-11 through T-19)
- `test: update patch targets for route module split` (T-20)
- `test: add CSRF enforcement tests` (T-21)
- `test: add auth bypass and security tests` (T-22)
- `test: add registration consistency tests` (T-23)
- `test: cover untested HTMX routes` (T-24)
- `test: add edge case tests` (T-25)
- `test: add extracted service tests` (T-26)
- `test: fill coverage gaps to 90%+` (T-27)

## Plan History

- 2026-02-28: Initial plan created from codebase audit
