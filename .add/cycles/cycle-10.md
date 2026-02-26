# Cycle 10 — RBAC & Protected Routes

**Milestone:** M9 — Multi-User
**Maturity:** beta
**Status:** COMPLETE
**Started:** 2026-02-25
**Completed:** 2026-02-25
**Duration Budget:** 1 day (6+ hours autonomous)

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| Role-Based Access Control | SPECCED | IN_PROGRESS | Agent-1 | ~8h | RBAC enforcement on all endpoints, protected routes, all tests passing |

## Scope (Plan Phase 3)

From `docs/plans/user-management-plan.md`, Phase 3 covers:

- **AC-006**: Admin can view, create, edit, delete all resources and manage users
- **AC-007**: Operator can view all resources, create sync logs, manage webhooks, but cannot delete or manage users
- **AC-008**: Viewer can view resources only (read-only access)
- **AC-010**: Protected routes redirect unauthenticated users to `/login`

### Tasks

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-020 | Create `require_role()` dependency factory in `app/api/deps.py` | 45min | Phase 2 complete |
| TASK-021 | Create `get_optional_user()` dependency for UI routes (returns User or None) | 30min | TASK-020 |
| TASK-022 | Add auth middleware for HTMX routes — redirect unauthenticated to `/login` | 1h | TASK-021 |
| TASK-023 | Apply `require_role(ROLE_ADMIN)` to admin-only API endpoints (delete sync logs) | 30min | TASK-020 |
| TASK-024 | Apply `require_role(ROLE_OPERATOR)` to write API endpoints (submit logs, manage webhooks) | 45min | TASK-020 |
| TASK-025 | Apply auth + role checks to all HTMX UI routes (dashboard, settings, webhooks, etc.) | 1.5h | TASK-021, TASK-022 |
| TASK-026 | Add user context to templates — username display, conditional nav, logout | 1h | TASK-025 |
| TASK-027 | Add `POST /logout` route (clear cookie, redirect to `/login`) | 30min | — |
| TASK-028 | Write RED tests for RBAC enforcement (~25-30 test cases) | 2h | TASK-020 |
| TASK-029 | GREEN: make all RBAC tests pass | 1h | TASK-028 |

## Dependencies & Serialization

```
Phase 2 complete (cycle-9 merged, PR #14) ✓
    ↓
TASK-020 (require_role factory) + TASK-027 (logout route) — parallel
    ↓
TASK-021 (get_optional_user) + TASK-022 (auth middleware)
    ↓
TASK-023 (admin API RBAC) + TASK-024 (operator API RBAC) — parallel
    ↓
TASK-025 (HTMX route auth) + TASK-026 (template user context) — sequential
    ↓
TASK-028 (RED tests) → TASK-029 (GREEN implementation)
```

## Parallel Strategy

Single-threaded execution. Solo developer, one agent.

## Validation Criteria

### Per-Item Validation
- **RBAC Enforcement**: AC-006, AC-007, AC-008, AC-010 all covered by passing tests
  - Admin can access all endpoints (200/201/204)
  - Operator can submit sync logs (POST) and manage webhooks but cannot delete sync logs (403)
  - Viewer can only read (GET) — all write operations return 403
  - Unauthenticated requests to UI routes redirect to `/login?return_url=...`
  - Unauthenticated requests to API routes return 401
  - `require_role()` factory returns 403 for insufficient role
  - Expired/invalid JWT in cookie redirects to `/login`
  - API key auth still works for API endpoints (backward compatibility)
  - Settings page requires Operator+ role
  - User context available in all authenticated templates
  - Logout clears cookie and redirects to `/login`

### Cycle Success Criteria
- [x] All 4 acceptance criteria (AC-006, AC-007, AC-008, AC-010) implemented
- [x] `require_role()` dependency factory working
- [x] All API endpoints have appropriate role checks
- [x] All HTMX routes redirect unauthenticated users to `/login`
- [x] Permission matrix fully tested (3 roles × key endpoints)
- [x] 32 RBAC tests written and passing (target was 25+)
- [x] Full test suite passes — 514 tests, 0 failures
- [x] ruff check clean
- [x] mypy clean — 0 errors in 43 source files
- [x] Coverage 91% (threshold 80%)
- [x] PR created on feature branch

## Implementation Details

### `require_role()` Pattern

```python
# app/api/deps.py
def require_role(minimum_role: str) -> Callable:
    async def _check(user: CurrentUserDep) -> User:
        if not role_at_least(user.role, minimum_role):
            raise HTTPException(status_code=403, detail=f"Requires {minimum_role} role")
        return user
    return Depends(_check)

# Type aliases
AdminDep = Annotated[User, require_role(ROLE_ADMIN)]
OperatorDep = Annotated[User, require_role(ROLE_OPERATOR)]
ViewerDep = Annotated[User, require_role(ROLE_VIEWER)]
```

### Auth Middleware for UI Routes

```python
# app/middleware.py — AuthRedirectMiddleware
PUBLIC_PATHS = {"/login", "/register", "/health", "/metrics", "/static"}
API_PREFIX = "/api/"

class AuthRedirectMiddleware:
    async def dispatch(self, request, call_next):
        path = request.url.path
        # Skip public paths and API routes (API has its own auth)
        if any(path.startswith(p) for p in PUBLIC_PATHS) or path.startswith(API_PREFIX):
            return await call_next(request)
        # Check JWT cookie
        token = request.cookies.get("access_token")
        if not token or not _validate_token(token):
            return RedirectResponse(f"/login?return_url={path}")
        return await call_next(request)
```

### Endpoint Protection Map

| Endpoint | Auth | Min Role | Notes |
|----------|:----:|----------|-------|
| `GET /` | JWT cookie | viewer | Dashboard |
| `GET /settings` | JWT cookie | operator | Settings page |
| `GET /login` | None | — | Public |
| `GET /register` | None | — | Public |
| `POST /login` | None | — | Public |
| `POST /register` | None | — | Public |
| `POST /logout` | JWT cookie | — | Clear cookie |
| `GET /health` | None | — | Public |
| `GET /metrics` | None | — | Public (Prometheus) |
| `GET /htmx/*` | JWT cookie | viewer | All HTMX partials |
| `POST /htmx/webhooks` | JWT cookie | operator | Create webhook |
| `PUT /htmx/webhooks/*` | JWT cookie | operator | Update webhook |
| `DELETE /htmx/webhooks/*` | JWT cookie | operator | Delete webhook |
| `POST /api/v1/sync-logs` | API key/JWT | operator | Submit logs |
| `DELETE /api/v1/sync-logs/*` | JWT | admin | Delete logs |
| `GET /api/v1/sync-logs` | API key/JWT | viewer | Query logs |
| `POST /api/v1/auth/*` | None | — | Auth endpoints |

### Backward Compatibility

- Existing API key auth (`X-API-Key` header) continues to work for API endpoints
- API keys are treated as `operator` role by default (can submit logs)
- JWT auth takes precedence when both are present
- No changes to existing API key model in this cycle

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
- Do NOT start Phase 4 (Per-User API Keys) — that's cycle-11
- Do NOT make architecture decisions outside the plan scope
- If blocked, log the blocker and stop

## Notes

- `require_role()` builds on existing `has_permission()` and `role_at_least()` from `app/services/auth.py`
- `get_current_user` dependency already exists in `app/api/deps.py` — handles JWT from header and cookie
- `CurrentUserDep` type alias already defined — use it as base for role-checking deps
- HTMX routes in `app/main.py` need auth but currently have no auth checks
- API routes in `app/api/endpoints/sync_logs.py` use `verify_api_key` — need dual auth (API key OR JWT)
- Templates need `user` in context for username display and role-conditional rendering
- The CSRF middleware already skips API routes — auth middleware should follow same pattern
