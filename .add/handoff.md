# Session Handoff
**Written:** 2026-02-25

## In Progress
- Nothing currently in progress — cycle-11 is complete and PR submitted

## Completed This Session
- Fixed RBAC test infrastructure (JWT secret key mismatch, auth fixtures, unauth_client)
- All 514 tests passing → committed as `239ef58`
- Fixed mypy errors in deps.py (Settings type annotations)
- Pushed `feature/rbac-protected-routes`, created PR #15 (cycle-10: RBAC & Protected Routes)
- Planned and executed cycle-11 (Per-User API Keys — AC-011, AC-012):
  - Added `user_id` FK and `role_override` to ApiKey model
  - Created API key CRUD endpoints (POST/GET/DELETE /api/v1/api-keys)
  - Updated `verify_api_key_or_jwt` to load associated user and enforce effective role
  - Created API key management UI in settings (HTMX)
  - 21 new tests, 535 total passing
  - Pushed `feature/per-user-api-keys`, created PR #16

## Decisions Made
- API key prefix: `rsv_` + 32-byte token_urlsafe
- Legacy keys (no user_id) treated as operator-level access
- `role_override` validated at key creation (must be <= user's role)
- API key auth loads user from DB when key has user_id
- `_get_api_key_effective_role()` priority: role_override > user.role > operator default
- PR #16 bases on `feature/rbac-protected-routes` (PR #15) to maintain clean history

## Blockers
- PR #15 (cycle-10) needs human review/merge before PR #16 can merge to main
- Test DB required `DROP TABLE api_keys` + recreate for new columns (production will need ALTER TABLE migration)

## Next Steps
1. Review and merge PR #15 (cycle-10: RBAC)
2. Review and merge PR #16 (cycle-11: Per-User API Keys)
3. Plan cycle-12 for Phase 5: Admin User Management + Password Reset (AC-006 admin UI, AC-013 password reset)
4. Production deployment and DB migration for new columns
