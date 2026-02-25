# M9 — Multi-User

**Goal:** Add user accounts, JWT authentication, role-based access control, and per-user API keys to support shared homelab environments
**Status:** LATER
**Appetite:** 2 weeks
**Target Maturity:** beta → ga
**Started:** —
**Completed:** —

## Success Criteria

- [ ] User registration and login with bcrypt/argon2 password hashing
- [ ] JWT access tokens with configurable expiry and refresh token support
- [ ] Three roles (Admin, Operator, Viewer) with enforced permission boundaries
- [ ] Login page at `/login` with redirect to original URL after auth
- [ ] Protected routes redirect unauthenticated users to login
- [ ] Per-user API keys with role-scoped permissions
- [ ] First registered user automatically gets Admin role
- [ ] Admin user management UI (list users, change roles, enable/disable)
- [ ] Password reset flow via email

## Hill Chart

```
User Accounts & Auth   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Role-Based Access      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Login & Protected UI   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Per-User API Keys      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Admin Management       ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
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
| — | — | — | Cycles to be planned when milestone starts |

## Retrospective

—
