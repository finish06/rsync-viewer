# Cycle 14 — E2E Playwright Happy Path Suite

**Milestone:** M-GA — GA Maintenance
**Maturity:** ga
**Status:** PLANNED
**Started:** TBD
**Completed:** TBD
**Duration Budget:** 1 day (autonomous)

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| E2E Playwright Happy Paths | SPECCED | VERIFIED | Agent-1 | ~4h | All 22 ACs passing, all 8 TCs covered, tests pass against local stack |

## Dependencies & Serialization

No external dependencies. All features under test are already implemented and stable.

Internal serialization: Infrastructure (conftest/fixtures) must be built first, then page tests can proceed independently.

```
Phase 1: Infrastructure (conftest, fixtures, helpers)
    ↓
Phase 2: Page tests (independent, can be written in any order)
    ↓
Phase 3: Validation (full suite run, timing check)
```

## Implementation Phases

### Phase 1: Test Infrastructure (~45min)
- **TASK-001:** Create `tests/e2e/conftest.py` with shared fixtures:
  - `base_url` fixture (from `E2E_BASE_URL` env var, default `http://localhost:8000`)
  - `test_user` fixture — registers a unique user via API, returns credentials
  - `admin_user` fixture — registers admin user (or uses default first-user-is-admin behavior)
  - `authenticated_page` fixture — logs in via browser, returns Page with auth cookies
  - `admin_page` fixture — logs in as admin, returns Page
  - `api_key` fixture — creates an API key for the test user via UI or API
  - Helper: `ingest_sync_log(api_key, source_name)` — POSTs a sync log via API

### Phase 2: Page Tests (~2.5h)
- **TASK-010:** `tests/e2e/test_login.py` — TC-001 (login flow)
- **TASK-011:** `tests/e2e/test_registration.py` — TC-002 (registration flow)
- **TASK-012:** `tests/e2e/test_dashboard.py` — TC-003 (dashboard data display, HTMX partials)
- **TASK-013:** `tests/e2e/test_analytics.py` — TC-003 variant (analytics page renders)
- **TASK-014:** `tests/e2e/test_settings.py` — TC-007 (settings tabs, HTMX tab switching)
- **TASK-015:** `tests/e2e/test_api_keys.py` — TC-004 (API key CRUD lifecycle)
- **TASK-016:** `tests/e2e/test_webhooks.py` — TC-005 (webhook CRUD lifecycle)
- **TASK-017:** `tests/e2e/test_admin_users.py` — TC-006 (admin user management)
- **TASK-018:** `tests/e2e/test_password_reset.py` — TC-008 (forgot password flow)

### Phase 3: Validation (~30min)
- **TASK-020:** Run full E2E suite against local stack, verify all pass
- **TASK-021:** Verify total runtime < 3 minutes
- **TASK-022:** Run existing test suite (`pytest tests/` excluding e2e) to confirm no regressions

## Validation Criteria

### Per-Item Validation
- AC-001–004 (infrastructure): Conftest provides all fixtures, tests are self-contained
- AC-010–019 (page coverage): Each page has at least one passing happy-path test
- AC-020–022 (HTMX): Dashboard, settings, and CRUD pages verify HTMX DOM updates
- AC-030–032 (quality): All pass, under 3 min, no inter-test dependencies

### Cycle Success Criteria
- [ ] All 22 acceptance criteria addressed
- [ ] 8 test case scenarios (TC-001 through TC-008) have passing Playwright tests
- [ ] Full E2E suite passes against `docker-compose up -d` local stack
- [ ] Total E2E runtime < 3 minutes
- [ ] Existing pytest suite still passes (no regressions)
- [ ] Feature branch with PR ready for human review

## Agent Autonomy & Checkpoints

Autonomous mode. Agent executes full cycle on feature branch, commits incrementally (phase by phase), creates PR when done. Human reviews on return.

**Checkpoint triggers:**
- After Phase 1: Commit infrastructure
- After each Phase 2 test file: Commit individually
- After Phase 3: Final validation, create PR

## Technical Notes

- Tests run against `http://localhost:8000` (override via `E2E_BASE_URL`)
- Requires `docker-compose up -d` running before test execution
- Requires `playwright` Python package + browser binaries (`playwright install`)
- Pattern follows existing `tests/e2e/test_changelog_playwright.py`
- Each test file creates unique users/data with UUID-based names
- No CI integration this cycle (local-only)

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Playwright not installed | Document install step in test README; check in conftest |
| First user auto-admin race condition | Create admin user first in session-scoped fixture |
| HTMX timing — partials load async | Use Playwright `expect` with auto-retry/wait, not sleep |
| CSRF tokens on form submissions | Extract CSRF token from page before submitting forms |
| Test pollution across runs | UUID-based usernames/data, no cleanup required |

## Spec & Plan References

- Spec: specs/e2e-playwright-happy-path.md
- Plan: This cycle document serves as the plan (single feature, straightforward implementation)
