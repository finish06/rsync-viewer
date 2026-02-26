# Cycle 11 — Per-User API Keys

**Milestone:** M9 — Multi-User
**Maturity:** beta
**Status:** IN_PROGRESS
**Started:** 2026-02-25
**Completed:** TBD
**Duration Budget:** 1 day (6+ hours autonomous)

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| Per-User API Keys | SPECCED | IN_PROGRESS | Agent-1 | ~8h | API key CRUD, role scoping, legacy compat, all tests passing |

## Scope (Plan Phase 4)

From `docs/plans/user-management-plan.md`, Phase 4 covers:

- **AC-011**: Per-user API keys can be generated, listed, and revoked from user settings
- **AC-012**: API key permissions are scoped to the user's role

### Tasks

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-028 | Add `user_id` (FK) and `role_override` columns to ApiKey model | 30min | Phase 3 complete |
| TASK-029 | Create API key CRUD endpoints: POST /api/v1/api-keys, GET /api/v1/api-keys, DELETE /api/v1/api-keys/{id} | 1.5h | TASK-028 |
| TASK-030 | Update `verify_api_key` and `verify_api_key_or_jwt` to load associated user and enforce role | 1h | TASK-028 |
| TASK-031 | Create user settings page template with API keys tab | 1h | — |
| TASK-032 | Add HTMX routes for API key management UI | 1h | TASK-029, TASK-031 |
| TASK-033 | Handle migration: existing API keys (no user_id) remain functional with operator role | 30min | TASK-028 |
| TASK-034 | Write RED tests for per-user API keys (generate, list, revoke, role scoping, legacy key compat) | 1.5h | TASK-029 |
| TASK-035 | GREEN: make API key tests pass | 1h | TASK-034 |

## Dependencies & Serialization

```
Phase 3 complete (cycle-10, PR #15) ✓
    ↓
TASK-028 (model changes)
    ↓
TASK-029 (API endpoints) + TASK-030 (verify_api_key update) — parallel
    ↓
TASK-031 (settings template) + TASK-032 (HTMX routes) — sequential
    ↓
TASK-033 (legacy compat)
    ↓
TASK-034 (RED tests) → TASK-035 (GREEN)
```

## Parallel Strategy

Single-threaded execution. Solo developer, one agent.

## Validation Criteria

### Per-Item Validation
- **Per-User API Keys**: AC-011, AC-012 covered by passing tests
  - Authenticated users can generate API keys (POST /api/v1/api-keys returns key)
  - Users can list their own API keys (GET /api/v1/api-keys)
  - Users can revoke their own keys (DELETE /api/v1/api-keys/{id})
  - Admin can list/revoke all users' keys
  - Generated key is shown once (plaintext); only hash stored in DB
  - API key auth loads associated user and enforces user's role
  - `role_override` allows scoping key below user's role
  - Legacy API keys (no user_id) remain functional with operator-level access
  - User settings page shows API key management UI
  - Key prefix visible in list for identification

### Cycle Success Criteria
- [ ] Both acceptance criteria (AC-011, AC-012) implemented
- [ ] API key CRUD endpoints working
- [ ] `verify_api_key` loads associated user and enforces role
- [ ] Legacy keys backward compatible
- [ ] Per-user API key tests written and passing
- [ ] Full test suite passes — 0 failures
- [ ] ruff check clean
- [ ] mypy clean
- [ ] Coverage >= 80%
- [ ] PR created on feature branch

## API Contract

### POST /api/v1/api-keys
Generate a new API key for the authenticated user.

**Request:**
```json
{
  "name": "My Script Key",
  "role_override": "viewer"  // optional, must be <= user's role
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "name": "My Script Key",
  "key": "rsv_abc123...full-key-shown-once",
  "key_prefix": "rsv_abc1",
  "role": "viewer",
  "created_at": "2026-02-25T..."
}
```

### GET /api/v1/api-keys
List current user's API keys (admin: all keys).

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "My Script Key",
    "key_prefix": "rsv_abc1",
    "role": "viewer",
    "is_active": true,
    "created_at": "...",
    "last_used_at": "..."
  }
]
```

### DELETE /api/v1/api-keys/{id}
Revoke an API key. Users can revoke own keys; admins can revoke any.

**Response:** 204 No Content

## Agent Autonomy & Checkpoints

**Mode:** Away (8 hours autonomous)

Elevated autonomy:
- Commit to feature branch freely (conventional commits)
- Push regularly so work is not lost
- Run and fix quality gates without asking
- Log progress in away-log

Boundaries:
- Do NOT merge to main
- Do NOT start Phase 5 unless Phase 4 is fully verified
- Do NOT make architecture decisions outside the plan scope
- If blocked, log the blocker and move to docs/cleanup tasks

## Notes

- ApiKey model currently has no user_id — need to add nullable FK
- `verify_api_key_or_jwt` returns `(User, ApiKey)` — when API key has user_id, load the user
- Key generation: use `secrets.token_urlsafe(32)` with `rsv_` prefix
- Store only the bcrypt hash, show plaintext key only once at creation
- The `role_override` field allows creating keys with permissions below the user's role (e.g., admin creates viewer-only key)
