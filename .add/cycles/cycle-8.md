# Cycle 8 — User Model & Registration

**Milestone:** M9 — Multi-User
**Maturity:** beta
**Status:** PLANNED
**Started:** TBD
**Completed:** TBD
**Duration Budget:** 1 day (6+ hours autonomous)

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| User Accounts & Auth | SHAPED | IN_PROGRESS | Agent-1 | ~7h | User model created, registration endpoint working, first-user-admin logic, all tests passing |

## Scope (Plan Phase 1)

From `docs/plans/user-management-plan.md`, Phase 1 covers:

- **AC-001**: Users can register with username, email, and password
- **AC-002**: Passwords are hashed with bcrypt before storage
- **AC-005**: Three roles exist: Admin, Operator, Viewer
- **AC-015**: First registered user automatically gets Admin role

### Tasks

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-001 | Add PyJWT to requirements.txt | 15min | — |
| TASK-002 | Create `app/models/user.py` with User model | 1h | — |
| TASK-003 | Create `app/schemas/user.py` with UserCreate, UserResponse schemas | 30min | TASK-002 |
| TASK-004 | Create `app/services/auth.py` with hash_password, verify_password, role constants, permission matrix | 1h | — |
| TASK-005 | Create `app/api/endpoints/auth.py` with POST /api/v1/auth/register | 1h | TASK-002, TASK-003, TASK-004 |
| TASK-006 | Add JWT config settings to app/config.py | 30min | — |
| TASK-007 | Write RED tests for registration | 1.5h | TASK-005 |
| TASK-008 | GREEN: make registration tests pass | 1h | TASK-007 |

## Dependencies & Serialization

```
Single-threaded execution. All tasks are sequential within Phase 1.

TASK-001 (PyJWT dep)
TASK-002 (User model) + TASK-004 (auth service) — can start in parallel
    ↓
TASK-003 (schemas) + TASK-006 (config)
    ↓
TASK-005 (registration endpoint)
    ↓
TASK-007 (RED tests) → TASK-008 (GREEN implementation)
```

## Parallel Strategy

Single-threaded execution. Solo developer, one agent.

## Validation Criteria

### Per-Item Validation
- **User Accounts & Auth**: AC-001, AC-002, AC-005, AC-015 all covered by passing tests
  - User model has all required fields (id, username, email, password_hash, role, is_active, timestamps)
  - Registration endpoint validates input (unique username/email, password strength)
  - Passwords hashed with bcrypt (not stored plaintext)
  - First registered user gets "admin" role, subsequent users get "viewer"
  - Role enum/constants defined for Admin, Operator, Viewer

### Cycle Success Criteria
- [ ] User model created with all spec fields
- [ ] Registration API endpoint returns 201 with user data
- [ ] Duplicate username/email returns 409
- [ ] Weak password returns 400
- [ ] First user gets Admin role automatically
- [ ] All new tests pass
- [ ] Full test suite passes (no regressions)
- [ ] ruff check clean
- [ ] mypy clean
- [ ] Coverage >= 80%
- [ ] PR created on feature/user-management branch

## Agent Autonomy & Checkpoints

**Mode:** Away (6+ hours autonomous)

Elevated autonomy:
- Commit to feature/user-management branch freely
- Push regularly so work is not lost
- Create PR when phase is complete
- Run and fix quality gates without asking
- Log progress in away-log

Boundaries:
- Do NOT merge to main
- Do NOT start Phase 2 (JWT auth) — that's cycle-9
- Do NOT make architecture decisions outside the plan scope
- If blocked, log the blocker and stop

## Notes

- Existing bcrypt dependency already in requirements.txt — reuse for password hashing
- PyJWT needed now (config prep) even though JWT auth is Phase 2
- ApiKey model modifications (user_id FK) deferred to Phase 4 (cycle-9 or cycle-10)
- OAuth login (AC-014) deferred to M7 OIDC milestone entirely
- Production DB will need manual CREATE TABLE for new `users` table
