# Cycle 12 — Admin Management, Password Reset & Session Timeout

**Milestone:** M9 — Multi-User
**Maturity:** beta
**Status:** COMPLETE
**Started:** 2026-02-26
**Completed:** 2026-02-26
**Duration Budget:** 2 days

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| Admin User Management | SHAPED | VERIFIED | Agent-1 | ~6h | AC-006 admin UI, safety checks, all tests passing |
| Password Reset | SHAPED | VERIFIED | Agent-1 | ~4h | AC-013 reset flow, token-in-logs, self-service + admin-initiated |
| Session Timeout | SHAPED | VERIFIED | Agent-1 | ~1h | AC-016 HTMX 401 interceptor with re-login modal |

## Scope

### Admin User Management (AC-006)
- **Page:** Separate `/admin/users` page (admin-only, visible in nav for admin role)
- **API:** GET /api/v1/users (admin list), PUT /api/v1/users/{id}/role, PUT /api/v1/users/{id}/status, DELETE /api/v1/users/{id}
- **HTMX:** User list table, role change dropdown, enable/disable toggle, delete with confirmation
- **Safety:** Cannot demote/delete self, at least one admin must exist
- **Tests:** Admin CRUD, role changes, safety checks, permission enforcement

### Password Reset (AC-013)
- **Mode:** Console logging (token printed to app logs, no SMTP)
- **Self-service:** "Forgot Password" link on login page → enter email → token logged → reset form
- **Admin-initiated:** "Reset Password" button on admin user list → generates token for that user
- **API:** POST /api/v1/auth/password-reset/request, POST /api/v1/auth/password-reset/confirm
- **Edge cases:** Token single-use, token expiry (1 hour), invalid token handling
- **Tests:** Request reset, confirm reset, expired token, used token, admin-initiated reset

### Session Timeout (AC-016)
- **Behavior:** HTMX 401 interceptor shows re-login modal without losing current page
- **Implementation:** htmx:responseError event listener, modal overlay with login form
- **Tests:** Verify 401 triggers re-login prompt

## Tasks

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-036 | Create admin user management page template at /admin/users | 1.5h | — | AC-006 |
| TASK-037 | Add admin user API endpoints (GET /api/v1/users, PUT role, PUT status, DELETE) | 1h | — | AC-006 |
| TASK-038 | Add HTMX routes for admin user list, role change, enable/disable, delete | 1.5h | TASK-036, TASK-037 | AC-006 |
| TASK-039 | Safety checks: cannot demote/delete self, at least one admin | 30min | TASK-037 | AC-006 |
| TASK-040 | Password reset endpoints (request + confirm), token logged to console | 1h | — | AC-013 |
| TASK-041 | Password reset UI: forgot password link on login, reset form page | 1h | TASK-040 | AC-013 |
| TASK-042 | Admin-initiated password reset button on admin user list | 30min | TASK-038, TASK-040 | AC-013 |
| TASK-043 | HTMX 401 interceptor: session timeout re-login modal | 1h | — | AC-016 |
| TASK-044 | Write RED tests for admin management (CRUD, safety, permissions) | 1.5h | TASK-037 | AC-006 |
| TASK-045 | Write RED tests for password reset (request, confirm, expiry, admin-initiated) | 1h | TASK-040 | AC-013 |
| TASK-046 | Write RED tests for session timeout interceptor | 30min | TASK-043 | AC-016 |
| TASK-047 | GREEN: make all tests pass | 2h | TASK-044, TASK-045, TASK-046 | All |
| TASK-048 | REFACTOR + VERIFY: cleanup, full suite, ruff, mypy, coverage | 1h | TASK-047 | — |

## Dependencies & Serialization

```
TASK-036 (admin template) + TASK-037 (admin API) — parallel
    ↓
TASK-038 (admin HTMX routes) + TASK-039 (safety checks)
    ↓
TASK-040 (password reset endpoints) — can start independently
    ↓
TASK-041 (reset UI) + TASK-042 (admin-initiated reset)
    ↓
TASK-043 (session timeout) — independent
    ↓
TASK-044, TASK-045, TASK-046 (RED tests)
    ↓
TASK-047 (GREEN)
    ↓
TASK-048 (REFACTOR + VERIFY)
```

## Parallel Strategy

Single-threaded execution. Solo developer, one agent. Features advance sequentially within the cycle.

## Validation Criteria

### Per-Item Validation
- **Admin User Management (AC-006):**
  - Admin can list all users at /admin/users
  - Admin can change user roles via dropdown
  - Admin can enable/disable user accounts
  - Admin can delete users (with confirmation)
  - Cannot demote or delete own account
  - At least one admin must always exist
  - Non-admin users get 403 on admin endpoints
- **Password Reset (AC-013):**
  - "Forgot Password" link on login page works
  - Reset token generated and logged to console
  - Reset form accepts token + new password
  - Token is single-use (second use rejected)
  - Token expires after 1 hour
  - Admin can trigger reset for any user
- **Session Timeout (AC-016):**
  - Expired JWT on HTMX request shows re-login modal
  - Re-login preserves current page context

### Cycle Success Criteria
- [x] All three acceptance criteria (AC-006 admin UI, AC-013, AC-016) implemented
- [x] Admin user management page functional with HTMX
- [x] Password reset flow working (console-logged tokens)
- [x] Session timeout re-login modal working
- [x] All new tests passing (33 new tests)
- [x] Full test suite passes (568 total)
- [x] ruff check and format clean
- [x] mypy clean
- [x] Coverage >= 80%
- [x] PR #18 created and merged

## Agent Autonomy & Checkpoints

**Mode:** Available (human present)

Beta balanced mode:
- Human approved this cycle plan
- Agent executes TDD cycle autonomously
- Human reviews PR before merge
- No deploy in this cycle (PR only)

## Notes

- PasswordResetToken table already exists in production DB (created during earlier migration)
- Password reset uses console logging only — no SMTP in MVP
- Admin-initiated reset = admin clicks button, token logged, admin shares reset link with user
- The `/admin/users` page should only appear in nav for admin-role users
- Existing rate limiting (slowapi) applies to auth endpoints including password reset
