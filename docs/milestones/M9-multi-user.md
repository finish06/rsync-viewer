# M9 — Multi-User

**Goal:** Add user accounts, JWT authentication, role-based access control, and per-user API keys to support shared homelab environments
**Status:** COMPLETE
**Appetite:** 2 weeks
**Target Maturity:** beta → ga
**Started:** 2026-02-24
**Completed:** 2026-02-26

## Success Criteria

- [x] User registration and login with bcrypt/argon2 password hashing
- [x] JWT access tokens with configurable expiry and refresh token support
- [x] Three roles (Admin, Operator, Viewer) with enforced permission boundaries
- [x] Login page at `/login` with redirect to original URL after auth
- [x] Protected routes redirect unauthenticated users to login
- [x] Per-user API keys with role-scoped permissions
- [x] First registered user automatically gets Admin role
- [x] Admin user management UI (list users, change roles, enable/disable)
- [x] Password reset flow (console-logged tokens, no SMTP in MVP)

## Hill Chart

```
User Accounts & Auth   ██████████████████████████████████████  DONE (Phases 1-2, PR #13, #14 merged)
Role-Based Access      ██████████████████████████████████████  DONE (Phase 3, 32 RBAC tests, PR #16 merged)
Login & Protected UI   ██████████████████████████████████████  DONE (login, register, middleware, logout)
Per-User API Keys      ██████████████████████████████████████  DONE (Phase 4, 21 tests, PR #17 merged)
Admin Management       ██████████████████████████████████████  DONE (Phase 5, 20 admin + 11 reset + 2 session tests, PR #18 merged)
Password Reset         ██████████████████████████████████████  DONE (console-logged tokens, self-service + admin-initiated)
Session Timeout        ██████████████████████████████████████  DONE (HTMX 401 interceptor with re-login)
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| User Registration & Login | specs/user-management.md | SHAPED | User model, password hashing, JWT tokens |
| Role-Based Access Control | specs/user-management.md | SHAPED | Admin/Operator/Viewer, permission middleware |
| Login UI & Protected Routes | specs/user-management.md | SHAPED | Login page, auth redirect, session timeout |
| Per-User API Keys | specs/user-management.md | SHAPED | Key generation, role scoping, revocation |
| Admin User Management | specs/user-management.md | SHAPED | User list, role changes, enable/disable |
| Password Reset | specs/user-management.md | SHAPED | Email-based reset flow with token |
| OAuth Login | specs/user-management.md | SHAPED | GitHub OAuth as alternative auth (stretch) |

## Dependencies

- M3 must be complete (security hardening provides rate limiting on auth endpoints, key hashing patterns, input validation)
- M3's API key hashing migration provides the pattern for user password hashing
- Logging (M3) needed for auth audit trails
- SMTP configuration needed for password reset emails

## Recommended Implementation Order

1. User model + registration + password hashing (data foundation)
2. JWT auth + login/refresh endpoints (auth infrastructure)
3. Login page UI + protected route middleware (frontend auth)
4. Role-Based Access Control middleware (permission enforcement)
5. Per-User API Keys (extend existing ApiKey model with user FK)
6. Admin User Management UI (admin panel)
7. Password Reset flow (email integration)
8. OAuth Login (stretch goal, if time permits)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Auth migration breaks existing API key users | High | High | Dual-mode transition: existing keys work without user, new keys require user |
| JWT secret management | Medium | High | Strong secret via env var, document rotation procedure |
| First-user-is-admin race condition | Low | Medium | Lock registration after first admin, or require invite |
| Password reset email deliverability | Medium | Medium | Log reset tokens in dev mode, document SMTP setup |
| OAuth adds third-party dependency | Low | Low | OAuth is optional (stretch goal) |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| cycle-8 | User Model & Registration (Phase 1) | COMPLETE | AC-001, AC-002, AC-005, AC-015. PR #13 merged. |
| cycle-9 | JWT Authentication & Login (Phase 2) | COMPLETE | AC-003, AC-004, AC-009. PR #14 merged. |
| cycle-10 | RBAC & Protected Routes (Phase 3) | COMPLETE | AC-006, AC-007, AC-008, AC-010. 32 tests, 514 total passing, 91% coverage. |
| cycle-11 | Per-User API Keys (Phase 4) | COMPLETE | AC-011, AC-012. 21 tests, 535 total passing, CRUD endpoints + role scoping + UI. |
| cycle-12 | Admin Management, Password Reset, Session Timeout (Phase 5) | COMPLETE | AC-006, AC-013, AC-016. 33 tests, 568 total passing, PR #18 merged. v1.8.0 released. |

## Retrospective

M9 completed in 5 cycles (cycle-8 through cycle-12) over 3 days. All 9 success criteria met:
- 5 TDD cycles with 568 total tests passing
- Full JWT auth with refresh token rotation
- 3-role RBAC (Admin, Operator, Viewer) with middleware enforcement
- Per-user API keys with role scoping
- Admin user management UI with HTMX
- Password reset via console-logged tokens
- Session timeout with HTMX 401 interceptor
- Released as v1.8.0
