# Spec: Codebase Hardening & Optimization

**Version:** 0.1.0
**Created:** 2026-02-28
**PRD Reference:** docs/prd.md
**Status:** Approved
**Milestone:** Pre-2.0 Preparation

## 1. Overview

Comprehensive codebase audit and refactoring to prepare for a 2.0 release. Break up the monolithic `app/main.py` (2,163 lines, 44 routes) into focused route modules, remove dead code, eliminate duplication, expand CSRF protection, centralize business logic into services, and raise test coverage from 83% to 90%+ with emphasis on edge cases, integration paths, and security testing.

### User Story

As a maintainer, I want a well-organized, thoroughly tested codebase with no dead code or duplicated logic, so that future feature development is faster, safer, and less error-prone.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | `app/main.py` is split into domain-specific route modules under `app/routes/`: auth, settings, dashboard, admin, webhooks, api_keys | Must |
| AC-002 | Each route module is a FastAPI `APIRouter` included in `main.py` — no route handlers remain directly on the `app` object (except health/metrics) | Must |
| AC-003 | All 27 redundant in-function imports in main.py are removed; only top-level imports are used | Must |
| AC-004 | `has_permission()` and `PERMISSIONS` dict in `auth.py` are removed (dead code — never called in production) along with their orphaned tests | Must |
| AC-005 | Hardcoded version strings (`"1.5.0"`) in `set_app_info()` and `FastAPI(version=)` are replaced with `settings.app_version` | Must |
| AC-006 | `CSRF_PROTECTED_PREFIXES` is expanded to cover all state-mutating HTMX routes: SMTP, OIDC, API keys, admin users (not just webhooks) | Must |
| AC-007 | Sync log filter logic (source, date range, dry run, hide empty) is extracted into a shared `_apply_sync_filters()` helper — no copy-paste duplication | Must |
| AC-008 | User registration logic is extracted into a service function called by both the HTMX route and the API endpoint — no duplicate implementations | Must |
| AC-009 | Webhook test payload construction is extracted into a service function shared by HTMX and API endpoints | Should |
| AC-010 | JWT decode calls in `deps.py` and `middleware.py` are consolidated to use the existing `decode_token()` from `auth.py` | Should |
| AC-011 | Admin role guard in HTMX routes uses a shared dependency (like `AdminDep`) instead of inline `if not user or not role_at_least(...)` repeated 10 times | Should |
| AC-012 | `RedirectResponse` imports are moved to module level (not imported inside function bodies) | Should |
| AC-013 | Test coverage reaches 90%+ overall | Must |
| AC-014 | All HTMX routes in new route modules have corresponding test coverage | Must |
| AC-015 | Security tests added: CSRF enforcement on all protected routes, auth bypass attempts on admin endpoints, injection testing on user inputs | Must |
| AC-016 | Edge case tests added: malformed rsync output, expired JWT handling, concurrent API key creation, empty database states | Should |
| AC-017 | No existing tests break after refactoring (zero regressions) | Must |
| AC-018 | `app/api/deps.py` consolidates duplicate bcrypt API key lookup logic (`_try_verify_api_key` and `verify_api_key` share near-identical code) | Should |

## 3. User Test Cases

### TC-001: All existing functionality works after route split

**Precondition:** Codebase refactored with route modules. Application running.
**Steps:**
1. Navigate to login page
2. Log in as admin
3. Visit dashboard, analytics, settings (SMTP, OIDC, API keys, webhooks), admin users
4. Submit a sync log via API
5. Create and revoke an API key
**Expected Result:** All pages render correctly. All CRUD operations succeed. No 500 errors.
**Screenshot Checkpoint:** N/A (functional verification)
**Maps to:** TBD

### TC-002: CSRF protection blocks unprotected mutations

**Precondition:** Admin logged in. CSRF token not included in request.
**Steps:**
1. Send POST to `/htmx/smtp-settings` without CSRF token
2. Send POST to `/htmx/settings/auth` without CSRF token
3. Send POST to `/htmx/api-keys` without CSRF token
4. Send PUT to `/htmx/admin/users/{id}/role` without CSRF token
**Expected Result:** All requests return 403 Forbidden.
**Maps to:** TBD

### TC-003: Registration service is consistent across UI and API

**Precondition:** No users exist in database.
**Steps:**
1. Register via UI form (`POST /register`)
2. Check user has Admin role (first user)
3. Register second user via API (`POST /api/v1/auth/register`)
4. Check user has Viewer role
5. Attempt duplicate username via both paths
**Expected Result:** Both paths enforce the same validation rules and role assignment. Duplicate username returns error from both.
**Maps to:** TBD

### TC-004: Coverage gate passes at 90%

**Precondition:** All new tests written.
**Steps:**
1. Run `pytest --cov=app --cov-fail-under=90`
**Expected Result:** Exit code 0. Coverage >= 90%.
**Maps to:** TBD

## 4. Data Model

No data model changes. This is a refactoring and testing effort only.

## 5. API Contract

No API changes. All existing endpoints retain their request/response contracts. Route paths are unchanged — only the internal file organization changes.

## 6. UI Behavior

No UI changes. All pages and HTMX interactions remain identical.

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Import of old `app.main` route symbols by external code | Routes are now on routers, but `app` still includes them — no breaking change |
| Tests that patch `app.main` functions directly | Must update patch targets to new module paths (e.g., `app.routes.settings`) |
| CSRF token present but invalid | Returns 403, same as missing token |
| Circular import from route modules importing services | Avoided by keeping route modules thin (call services, don't implement logic) |

## 8. Dependencies

- No new dependencies required
- All changes are internal refactoring
- Existing test infrastructure (pytest, httpx TestClient) is sufficient

## 9. Route Module Structure (Target)

```
app/
├── main.py                  # App creation, lifespan, middleware, router includes (~200 lines)
├── routes/
│   ├── __init__.py
│   ├── pages.py             # Page renders: index, analytics, login, register, settings
│   ├── auth.py              # Login POST, logout, OIDC login/callback, forgot/reset password
│   ├── dashboard.py         # HTMX: sync table, charts, detail modal, notifications tab
│   ├── settings.py          # HTMX: SMTP config, OIDC config
│   ├── api_keys.py          # HTMX: API key list, create, revoke
│   ├── webhooks.py          # HTMX: Webhook CRUD, toggle, test
│   └── admin.py             # HTMX: Admin user management
├── services/
│   ├── registration.py      # Shared registration logic (new)
│   ├── sync_filters.py      # Shared sync log query filters (new)
│   └── ...                  # Existing services unchanged
```

## 10. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-28 | 0.1.0 | finish06 | Initial spec from /add:spec interview + codebase audit |
