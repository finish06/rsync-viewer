# Cycle 9 — JWT Authentication & Login

**Milestone:** M9 — Multi-User
**Maturity:** beta
**Status:** PLANNED
**Started:** TBD
**Completed:** TBD
**Duration Budget:** 1 day (6+ hours autonomous)

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| User Accounts & Auth | IN_PROGRESS | IN_PROGRESS | Agent-1 | ~10h | JWT login, refresh, login UI, register UI — all tests passing |

## Scope (Plan Phase 2)

From `docs/plans/user-management-plan.md`, Phase 2 covers:

- **AC-003**: Users can log in and receive a JWT access token
- **AC-004**: JWT tokens expire after configurable period with refresh token support
- **AC-009**: Login page at `/login` with username/password form

### Tasks

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-009 | Add JWT encode/decode to `app/services/auth.py` (create_access_token, create_refresh_token, decode_token) | 1h | Phase 1 complete |
| TASK-010 | Create RefreshToken model in `app/models/user.py` (already exists, verify/enhance) | 30min | — |
| TASK-011 | Add POST /api/v1/auth/login endpoint (returns access_token + refresh_token) | 1h | TASK-009, TASK-010 |
| TASK-012 | Add POST /api/v1/auth/refresh endpoint | 45min | TASK-010 |
| TASK-013 | Create `get_current_user` FastAPI dependency (reads JWT from Authorization header or cookie) | 1h | TASK-009 |
| TASK-014 | Create login page template `app/templates/login.html` with form | 1h | — |
| TASK-015 | Add GET /login and POST /login HTMX routes (set JWT in httpOnly cookie) | 1h | TASK-011, TASK-014 |
| TASK-016 | Create registration page template `app/templates/register.html` | 45min | — |
| TASK-017 | Add GET /register HTMX route | 30min | TASK-016 |
| TASK-018 | Write RED tests for login, JWT issuance, refresh, invalid credentials | 1.5h | TASK-011 |
| TASK-019 | GREEN: make login/JWT tests pass | 1h | TASK-018 |

## Dependencies & Serialization

```
Phase 1 complete (cycle-8 merged) ✓
    ↓
TASK-009 (JWT service) + TASK-010 (RefreshToken model check) — parallel
    ↓
TASK-011 (login API) + TASK-012 (refresh API) + TASK-013 (get_current_user dep)
    ↓
TASK-014 (login template) + TASK-016 (register template) — parallel, no code deps
    ↓
TASK-015 (login HTMX routes) + TASK-017 (register HTMX route)
    ↓
TASK-018 (RED tests) → TASK-019 (GREEN implementation)
```

## Parallel Strategy

Single-threaded execution. Solo developer, one agent.

## Validation Criteria

### Per-Item Validation
- **JWT Auth**: AC-003, AC-004, AC-009 all covered by passing tests
  - POST /api/v1/auth/login returns access_token + refresh_token for valid credentials
  - POST /api/v1/auth/login returns 401 for invalid credentials
  - POST /api/v1/auth/login returns 403 for disabled accounts
  - JWT access token contains user_id, username, role claims
  - JWT access token expires after configured period (default 24h)
  - POST /api/v1/auth/refresh returns new access_token for valid refresh token
  - POST /api/v1/auth/refresh returns 401 for expired/revoked refresh token
  - `get_current_user` dependency extracts user from JWT in Authorization header
  - `get_current_user` dependency extracts user from JWT in httpOnly cookie
  - GET /login renders login form template
  - POST /login sets JWT in httpOnly cookie and redirects to dashboard
  - GET /register renders registration form template
  - Login page preserves return_url for post-login redirect
  - RefreshToken stored hashed in database, not plaintext

### Cycle Success Criteria
- [ ] Login endpoint returns JWT tokens for valid credentials
- [ ] Refresh endpoint rotates access tokens
- [ ] get_current_user dependency works with header and cookie
- [ ] Login page template renders and handles form submission
- [ ] Registration page template renders
- [ ] All new tests pass
- [ ] Full test suite passes (no regressions)
- [ ] ruff check clean
- [ ] mypy clean
- [ ] Coverage >= 80%
- [ ] PR created on feature branch

## Agent Autonomy & Checkpoints

**Mode:** Away (6+ hours autonomous)

Elevated autonomy:
- Commit to feature branch freely (conventional commits)
- Push regularly so work is not lost
- Create PR when phase is complete
- Run and fix quality gates without asking
- Log progress in away-log

Boundaries:
- Do NOT merge to main
- Do NOT start Phase 3 (RBAC) — that's cycle-10
- Do NOT make architecture decisions outside the plan scope
- If blocked, log the blocker and stop

## Notes

- RefreshToken model already exists in `app/models/user.py` from Phase 1 — verify it has all needed fields
- PyJWT already in requirements.txt from Phase 1
- JWT config settings already in `app/config.py` from Phase 1
- Use `secret_key` from existing config for JWT signing (no new secret needed)
- httpOnly cookie for JWT in HTMX routes, Authorization header for API routes
- Login template should match existing HTMX patterns (base.html layout)
- Registration page links from login page ("Don't have an account? Register")
