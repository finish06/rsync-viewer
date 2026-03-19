# Cycle 15 — E2E Playwright Error Scenarios

**Milestone:** M-GA — GA Maintenance
**Maturity:** ga
**Status:** PLANNED
**Started:** TBD
**Completed:** TBD
**Duration Budget:** 1 day (autonomous)

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| E2E Playwright Error Scenarios | SPECCED | VERIFIED | Agent-1 | ~2h | All 14 ACs passing, tests added to existing files, no regressions |

## Dependencies & Serialization

Depends on cycle 14 (PR #38) being merged first — the error tests extend the existing test files and conftest fixtures.

```
Cycle 14 (happy paths) — MUST BE MERGED
    ↓
Cycle 15 (error scenarios) — extends same files
```

## Implementation Phases

### Phase 1: Auth Error Tests (~30min)
- **TASK-101:** Add to `test_login.py`: invalid password, non-existent user, disabled account
- **TASK-102:** Add to `test_login.py`: CSRF token tampering on login form

### Phase 2: Session & RBAC Tests (~30min)
- **TASK-110:** Add to `test_login.py` or new section: unauthenticated access redirects (/, /settings, /admin/users)
- **TASK-111:** Add to `test_settings.py`: viewer user gets 403 on /settings
- **TASK-112:** Add to `test_admin_users_e2e.py`: viewer user gets 403 on /admin/users, cannot change roles

### Phase 3: Input Validation Tests (~30min)
- **TASK-120:** Add to `test_registration.py`: duplicate username, duplicate email, short password
- **TASK-121:** Add to `test_registration.py`: CSRF token tampering on register form

### Phase 4: Validation (~30min)
- **TASK-130:** Run full E2E suite (happy + error), verify all pass
- **TASK-131:** Run existing pytest suite (950+ tests) to confirm no regressions
- **TASK-132:** Lint + format check

## Validation Criteria

### Per-Item Validation
- AC-101–103: Login error messages display correctly, no redirect
- AC-110–111: Tampered CSRF tokens rejected
- AC-120–122: Unauthenticated access redirects to /login
- AC-130–132: Viewer role denied access to operator/admin pages
- AC-140–142: Registration validation errors display correctly

### Cycle Success Criteria
- [ ] All 14 acceptance criteria addressed
- [ ] Tests added to existing files (no new test files)
- [ ] Full E2E suite passes (happy + error tests)
- [ ] Existing 950+ pytest tests pass (no regressions)
- [ ] Lint + format clean
- [ ] Feature branch with PR ready for human review

## Agent Autonomy & Checkpoints

Autonomous mode. Agent executes full cycle on feature branch, commits incrementally, creates PR when done.

## Technical Notes

- Tests extend existing files from cycle 14 (must merge PR #38 first)
- Viewer user fixture already exists in conftest.py
- Disabled account test: register user, promote to admin, disable via DB, attempt login
- CSRF tamper: use `page.evaluate()` to modify hidden input value before submit
- Auth redirect: clear `access_token` cookie via `context.clear_cookies()` then navigate

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| PR #38 not merged yet | Branch from feature/e2e-playwright-happy-paths instead of main |
| CSRF rejection behavior varies (redirect vs error page) | Test for both: check URL changed OR error message present |
| Disabled account requires DB access | Reuse docker exec pattern from conftest promote_user_to_admin |

## Spec & Plan References

- Spec: specs/e2e-playwright-error-scenarios.md
- Depends on: specs/e2e-playwright-happy-path.md (cycle 14)
