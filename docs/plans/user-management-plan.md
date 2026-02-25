# Implementation Plan: User Management (M9)

**Spec Version**: 0.1.0
**Created**: 2026-02-24
**Team Size**: Solo
**Estimated Duration**: 2 weeks (5 phases)

## Overview

Add multi-user support with user accounts, JWT authentication, role-based access control (Admin/Operator/Viewer), and per-user API key management. Transforms rsync-viewer from a single-key app into a multi-user platform for shared homelab environments.

## Objectives

- User registration and login with bcrypt password hashing
- JWT access/refresh token authentication
- Three-tier RBAC (Admin, Operator, Viewer) enforced on all endpoints
- Per-user API keys scoped to user's role
- Login/register UI with protected route redirects
- Admin user management UI
- First registered user auto-assigned Admin role

## Success Criteria

- All 16 acceptance criteria implemented and tested
- Code coverage >= 80%
- All quality gates passing (ruff, mypy, pytest)
- Zero security vulnerabilities (no plaintext tokens, no injection)
- Backward compatibility: existing API key auth still works during migration

## Acceptance Criteria Analysis

### AC-001: User registration (Must)
- **Complexity**: Medium
- **Tasks**: User model, registration endpoint, validation (username uniqueness, email format, password strength)
- **Dependencies**: None (foundational)

### AC-002: Password hashing with bcrypt (Must)
- **Complexity**: Simple
- **Tasks**: Reuse existing bcrypt in deps.py, add hash_password/verify_password helpers
- **Dependencies**: AC-001

### AC-003: JWT access token on login (Must)
- **Complexity**: Medium
- **Tasks**: Add PyJWT dependency, create JWT service (encode/decode), login endpoint
- **Dependencies**: AC-001, AC-002

### AC-004: Configurable JWT expiry + refresh tokens (Must)
- **Complexity**: Medium
- **Tasks**: RefreshToken model, refresh endpoint, config settings (jwt_access_expiry, jwt_refresh_expiry)
- **Dependencies**: AC-003

### AC-005: Three roles — Admin, Operator, Viewer (Must)
- **Complexity**: Simple
- **Tasks**: Role enum, permission matrix constants, role field on User model
- **Dependencies**: AC-001

### AC-006: Admin full access (Must)
- **Complexity**: Medium
- **Tasks**: RBAC middleware/dependency, protect all admin-only endpoints
- **Dependencies**: AC-005

### AC-007: Operator permissions (Must)
- **Complexity**: Simple
- **Tasks**: Permission checks on webhook management, sync log submission
- **Dependencies**: AC-005, AC-006

### AC-008: Viewer read-only (Must)
- **Complexity**: Simple
- **Tasks**: Permission checks blocking write operations for Viewer role
- **Dependencies**: AC-005, AC-006

### AC-009: Login page at /login (Must)
- **Complexity**: Medium
- **Tasks**: Login template, form handling, JWT cookie/header management, error display
- **Dependencies**: AC-003

### AC-010: Protected route redirects (Must)
- **Complexity**: Medium
- **Tasks**: Auth middleware for HTMX routes, redirect to /login with return_url param
- **Dependencies**: AC-009

### AC-011: Per-user API keys (Must)
- **Complexity**: Medium
- **Tasks**: Add user_id FK to ApiKey, API key CRUD endpoints, user settings UI tab
- **Dependencies**: AC-001, AC-003

### AC-012: API key role scoping (Must)
- **Complexity**: Medium
- **Tasks**: Extend verify_api_key to load user and check role, add role_override field
- **Dependencies**: AC-011, AC-005

### AC-013: Password reset via email (Should)
- **Complexity**: High
- **Tasks**: PasswordResetToken model, SMTP config, reset request/confirm endpoints, email template
- **Dependencies**: AC-001, AC-002
- **Note**: Defer to later phase; can stub with token-in-logs for testing

### AC-014: OAuth login — GitHub (Should)
- **Complexity**: High
- **Tasks**: OAuth flow, GitHub provider, account linking
- **Dependencies**: AC-003
- **Note**: Defer entirely — M7 OIDC spec covers this more broadly

### AC-015: First user gets Admin role (Must)
- **Complexity**: Simple
- **Tasks**: Check user count in registration logic, assign "admin" if count == 0
- **Dependencies**: AC-001, AC-005

### AC-016: Session timeout re-login prompt (Should)
- **Complexity**: Medium
- **Tasks**: HTMX interceptor for 401 responses, modal/redirect to login preserving page state
- **Dependencies**: AC-009, AC-010

## Implementation Phases

### Phase 1: User Model & Registration (AC-001, AC-002, AC-005, AC-015)

Foundation — create User model and registration endpoint.

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-001 | Add PyJWT to requirements.txt | 15min | — | — |
| TASK-002 | Create `app/models/user.py` with User model (id, username, email, password_hash, role, is_active, timestamps) | 1h | — | AC-001, AC-005 |
| TASK-003 | Create `app/schemas/user.py` with UserCreate, UserResponse, UserLogin schemas | 30min | TASK-002 | AC-001 |
| TASK-004 | Create `app/services/auth.py` with hash_password, verify_password, role constants, permission matrix | 1h | — | AC-002, AC-005 |
| TASK-005 | Create `app/api/endpoints/auth.py` with POST /api/v1/auth/register | 1h | TASK-002, TASK-003, TASK-004 | AC-001, AC-015 |
| TASK-006 | Add config settings: jwt_secret_key, jwt_access_expiry_minutes, jwt_refresh_expiry_days | 30min | — | AC-004 |
| TASK-007 | Write RED tests for registration (valid, duplicate username/email, weak password, first-user-admin) | 1.5h | TASK-005 | AC-001, AC-002, AC-015 |
| TASK-008 | GREEN: make registration tests pass | 1h | TASK-007 | AC-001, AC-002, AC-015 |

**Phase Effort**: ~7h
**Files Created**: `app/models/user.py`, `app/schemas/user.py`, `app/services/auth.py`, `app/api/endpoints/auth.py`, `tests/test_user_registration.py`
**Files Modified**: `requirements.txt`, `app/config.py`, `app/main.py` (include router, import model for table creation)

### Phase 2: JWT Authentication & Login (AC-003, AC-004, AC-009)

Add JWT token issuance, refresh, and login page.

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-009 | Add JWT encode/decode to `app/services/auth.py` (create_access_token, create_refresh_token, decode_token) | 1h | TASK-004 | AC-003 |
| TASK-010 | Create RefreshToken model in `app/models/user.py` | 30min | TASK-002 | AC-004 |
| TASK-011 | Add POST /api/v1/auth/login endpoint (returns access_token + refresh_token) | 1h | TASK-009, TASK-010 | AC-003 |
| TASK-012 | Add POST /api/v1/auth/refresh endpoint | 45min | TASK-010 | AC-004 |
| TASK-013 | Create `get_current_user` FastAPI dependency (reads JWT from Authorization header or cookie) | 1h | TASK-009 | AC-003 |
| TASK-014 | Create login page template `app/templates/login.html` with form | 1h | — | AC-009 |
| TASK-015 | Add GET /login and POST /login HTMX routes (set JWT in httpOnly cookie) | 1h | TASK-011, TASK-014 | AC-009 |
| TASK-016 | Create registration page template `app/templates/register.html` | 45min | — | AC-001 |
| TASK-017 | Add GET /register HTMX route | 30min | TASK-016 | AC-001 |
| TASK-018 | Write RED tests for login, JWT issuance, refresh, invalid credentials | 1.5h | TASK-011 | AC-003, AC-004 |
| TASK-019 | GREEN: make login/JWT tests pass | 1h | TASK-018 | AC-003, AC-004 |

**Phase Effort**: ~10h
**Files Created**: `app/templates/login.html`, `app/templates/register.html`, `tests/test_jwt_auth.py`
**Files Modified**: `app/models/user.py`, `app/services/auth.py`, `app/api/endpoints/auth.py`, `app/api/deps.py`, `app/main.py`

### Phase 3: RBAC & Protected Routes (AC-006, AC-007, AC-008, AC-010)

Enforce role-based access on all endpoints and protect UI routes.

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-020 | Create `require_role` dependency factory in `app/api/deps.py` — takes minimum role, returns dependency | 1h | TASK-013 | AC-006 |
| TASK-021 | Create auth middleware for HTMX routes — check JWT cookie, redirect to /login with return_url | 1h | TASK-013 | AC-010 |
| TASK-022 | Apply `require_role("admin")` to admin-only endpoints (DELETE sync logs, user management) | 1h | TASK-020 | AC-006 |
| TASK-023 | Apply `require_role("operator")` to write endpoints (POST sync logs, webhook CRUD) | 1h | TASK-020 | AC-007 |
| TASK-024 | Protect all HTMX routes with auth middleware (dashboard, settings, etc.) | 1h | TASK-021 | AC-010 |
| TASK-025 | Add user info to template context (username in header, role-based nav visibility) | 45min | TASK-024 | AC-009 |
| TASK-026 | Write RED tests for RBAC (admin can delete, operator can create, viewer read-only, unauthenticated redirects) | 2h | TASK-022 | AC-006, AC-007, AC-008, AC-010 |
| TASK-027 | GREEN: make RBAC tests pass | 1.5h | TASK-026 | AC-006, AC-007, AC-008, AC-010 |

**Phase Effort**: ~9h
**Files Modified**: `app/api/deps.py`, `app/main.py`, `app/middleware.py`, `app/api/endpoints/sync_logs.py`, `app/api/endpoints/webhooks.py`, all HTMX template routes, `app/templates/base.html`
**Files Created**: `tests/test_rbac.py`

### Phase 4: Per-User API Keys (AC-011, AC-012)

Link API keys to users and scope permissions.

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-028 | Add `user_id` (FK) and `role_override` columns to ApiKey model | 30min | TASK-002 | AC-011 |
| TASK-029 | Create API key CRUD endpoints: POST /api/v1/api-keys (generate), GET /api/v1/api-keys (list user's keys), DELETE /api/v1/api-keys/{id} (revoke) | 1.5h | TASK-028, TASK-013 | AC-011 |
| TASK-030 | Update `verify_api_key` in deps.py to load associated user and enforce role | 1h | TASK-028 | AC-012 |
| TASK-031 | Create user settings page template with API keys tab | 1h | — | AC-011 |
| TASK-032 | Add HTMX routes for API key management UI | 1h | TASK-029, TASK-031 | AC-011 |
| TASK-033 | Handle migration: existing API keys (no user_id) remain functional with "admin" role | 30min | TASK-028 | AC-012 |
| TASK-034 | Write RED tests for per-user API keys (generate, list, revoke, role scoping, legacy key compat) | 1.5h | TASK-029 | AC-011, AC-012 |
| TASK-035 | GREEN: make API key tests pass | 1h | TASK-034 | AC-011, AC-012 |

**Phase Effort**: ~8h
**Files Modified**: `app/models/sync_log.py` (ApiKey), `app/api/deps.py`, `app/main.py`
**Files Created**: `app/templates/settings_account.html`, `tests/test_user_api_keys.py`

### Phase 5: Admin UI, Password Reset & Polish (AC-006, AC-013, AC-016)

Admin user management, password reset (Should), session timeout handling.

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-036 | Create admin user management page template at /admin/users | 1.5h | — | AC-006 |
| TASK-037 | Add GET /api/v1/users (admin-only list), PUT /api/v1/users/{id}/role (admin-only role change) | 1h | TASK-020 | AC-006 |
| TASK-038 | Add HTMX routes for admin user list, role change dropdown, enable/disable toggle, delete user | 1.5h | TASK-037 | AC-006 |
| TASK-039 | Implement safety checks: cannot demote/delete self, at least one admin must exist | 30min | TASK-037 | AC-006 |
| TASK-040 | Create PasswordResetToken model | 30min | — | AC-013 |
| TASK-041 | Add password reset endpoints (POST request, POST confirm) — token logged to console (no SMTP in MVP) | 1h | TASK-040 | AC-013 |
| TASK-042 | Add password reset UI (forgot password link, reset form) | 1h | TASK-041 | AC-013 |
| TASK-043 | Add HTMX 401 interceptor for session timeout — show re-login modal | 1h | — | AC-016 |
| TASK-044 | Write RED tests for admin management, password reset, session timeout | 2h | TASK-037 | AC-006, AC-013, AC-016 |
| TASK-045 | GREEN: make all Phase 5 tests pass | 1.5h | TASK-044 | AC-006, AC-013, AC-016 |
| TASK-046 | REFACTOR: clean up middleware ordering, consolidate auth logic, update .env.example | 1h | — | — |
| TASK-047 | VERIFY: full test suite, ruff, mypy, coverage check | 30min | TASK-046 | — |

**Phase Effort**: ~12h
**Files Created**: `app/templates/admin_users.html`, `app/templates/partials/user_list.html`, `app/templates/partials/password_reset.html`, `tests/test_admin_users.py`, `tests/test_password_reset.py`
**Files Modified**: `app/models/user.py`, `app/api/endpoints/auth.py`, `app/main.py`, `app/templates/login.html`, `.env.example`

## Effort Summary

| Phase | Estimated Hours | Description |
|-------|-----------------|-------------|
| Phase 1 | 7h | User Model & Registration |
| Phase 2 | 10h | JWT Auth & Login |
| Phase 3 | 9h | RBAC & Protected Routes |
| Phase 4 | 8h | Per-User API Keys |
| Phase 5 | 12h | Admin UI, Password Reset, Polish |
| **Total** | **46h** | **~2 weeks solo** |

## Dependencies

### New Package
- `PyJWT>=2.8.0` — JWT encoding/decoding (preferred over python-jose for simplicity)

### Existing Infrastructure (reused)
- `bcrypt` — already in requirements.txt for API key hashing
- `slowapi` — rate limiting on auth endpoints already configured
- CSRF middleware — already protects form POSTs
- Security headers — already in place

### Database Migration
- 3 new tables: `users`, `refresh_tokens`, `password_reset_tokens`
- 1 modified table: `api_keys` (add `user_id` FK, `role_override` column)
- `SQLModel.metadata.create_all(engine)` handles test DB automatically
- **Production:** requires manual `ALTER TABLE api_keys ADD COLUMN user_id UUID REFERENCES users(id)` and `CREATE TABLE` for new tables

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing API key auth during migration | High | Critical | Make user_id nullable on ApiKey, treat keyless keys as admin-equivalent, add migration path |
| JWT secret key management | Medium | High | Reuse existing `secret_key` from config, document rotation procedure |
| RBAC enforcement gaps | Medium | High | Comprehensive test matrix covering all role × endpoint combinations |
| Cookie security (JWT in httpOnly cookie) | Low | Medium | Set Secure, HttpOnly, SameSite=Lax flags; CSRF middleware already active |
| Template changes breaking existing UI | Medium | Medium | Incremental changes, test each template renders correctly |

## Testing Strategy

### Unit Tests (~50 tests estimated)
- User model validation (username, email, password strength)
- JWT encode/decode (valid, expired, tampered)
- Password hashing and verification
- Role permission matrix (3 roles × 10 resources = 30 combinations)
- API key role scoping

### Integration Tests (~30 tests estimated)
- Registration → login → access protected resource flow
- Refresh token rotation
- Admin user management operations
- API key generation and revocation
- Protected route redirects

### Coverage Targets
- `app/services/auth.py` — 95%+
- `app/api/endpoints/auth.py` — 90%+
- `app/api/deps.py` — 90%+
- `app/models/user.py` — 95%+

## Backward Compatibility

The migration must be non-breaking for existing deployments:

1. **API keys without user_id**: Treated as admin-equivalent (full access)
2. **Existing `/settings` route**: Still accessible, auth added on top
3. **Default API key (debug mode)**: Continues to work for development
4. **No forced registration**: Existing single-key mode works until first user registers; after that, auth is enforced

This is achieved by:
- Making `user_id` nullable on `ApiKey`
- Adding a config flag `auth_enabled: bool = False` (default off) — once first user registers, auto-enables
- Existing `verify_api_key` continues to work for API endpoints
- HTMX routes check auth only when `auth_enabled` is true

## Deferred Items

| Item | Reason | When |
|------|--------|------|
| AC-014: OAuth/GitHub login | Covered more broadly by M7 OIDC spec | M7 |
| SMTP email delivery | Use token-in-logs for MVP; add SMTP config later | Post-M9 |
| User profile photo/avatar | Not in spec, low priority | Post-GA |

## Files Summary

### New Files (13)
| File | Purpose |
|------|---------|
| `app/models/user.py` | User, RefreshToken, PasswordResetToken models |
| `app/schemas/user.py` | Pydantic schemas for auth requests/responses |
| `app/services/auth.py` | JWT, password hashing, permission matrix |
| `app/api/endpoints/auth.py` | Auth API endpoints (register, login, refresh, reset) |
| `app/templates/login.html` | Login page |
| `app/templates/register.html` | Registration page |
| `app/templates/settings_account.html` | User settings with API key management |
| `app/templates/admin_users.html` | Admin user management page |
| `app/templates/partials/user_list.html` | HTMX partial for user table |
| `app/templates/partials/password_reset.html` | HTMX partial for password reset form |
| `tests/test_user_registration.py` | Registration tests |
| `tests/test_jwt_auth.py` | JWT and login tests |
| `tests/test_rbac.py` | Role-based access control tests |
| `tests/test_user_api_keys.py` | Per-user API key tests |
| `tests/test_admin_users.py` | Admin user management tests |
| `tests/test_password_reset.py` | Password reset tests |

### Modified Files (8)
| File | Change |
|------|--------|
| `requirements.txt` | Add PyJWT |
| `app/config.py` | Add JWT settings, auth_enabled flag |
| `app/models/sync_log.py` | Add user_id FK and role_override to ApiKey |
| `app/api/deps.py` | Add get_current_user, require_role, update verify_api_key |
| `app/main.py` | Include auth router, import new models, add auth middleware to HTMX routes |
| `app/templates/base.html` | Add user info to header, login/logout links |
| `.env.example` | Add JWT and auth env vars |
| `app/middleware.py` | Add optional auth check middleware for HTMX routes |

## Next Steps

1. Review and approve this plan
2. Create cycle plan (cycle-8) with Phase 1-2 as first batch
3. Run `/add:tdd-cycle specs/user-management.md` to begin execution
4. Phase 3-5 in cycle-9

## Plan History

- 2026-02-24: Initial plan created
