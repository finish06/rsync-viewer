# Implementation Plan: OIDC Authentication

**Spec Version**: 0.1.0
**Created**: 2026-02-24
**Team Size**: Solo
**Estimated Duration**: 3-4 days

## Overview

Add OpenID Connect login as an optional authentication method alongside the existing API key auth. A single OIDC provider (PocketId or generic) is configured via environment variables. Users authenticating via OIDC get local accounts auto-created or auto-linked by email.

## Critical Dependency

**This spec depends on `specs/user-management.md` being implemented first.** The OIDC feature extends the User model, issues JWT sessions, and uses role-based access — all of which are defined in the user-management spec.

**However**, a subset of OIDC can be implemented independently by building the OIDC plumbing (discovery, auth flow, callback, token exchange) with a minimal User model. The plan below assumes user-management is implemented first, but Phase 1 (config + OIDC client) can start without it.

## Objectives

- Enable SSO login via any OIDC-compliant provider
- Auto-create and auto-link accounts based on OIDC claims
- Maintain backward compatibility (no OIDC = no changes to existing behavior)
- Secure the flow with state + nonce validation

## Success Criteria

- All 17 acceptance criteria implemented and tested
- Code coverage >= 80% for new OIDC code
- All quality gates passing (ruff, mypy, pytest)
- OIDC login works end-to-end with PocketId in Docker environment

## Acceptance Criteria Analysis

### AC-001: OIDC enabled via env vars
- **Complexity**: Simple
- **Effort**: 1h
- **Tasks**: Add OIDC settings to config.py, update .env.example
- **Testing**: Unit test that config loads correctly with/without OIDC vars

### AC-002: Provider-branded login button
- **Complexity**: Simple
- **Effort**: 1h
- **Tasks**: Update login template with conditional OIDC button
- **Dependencies**: Login page must exist (user-management spec)
- **Testing**: Template renders button when OIDC configured, hides when not

### AC-003: Authorization Code Flow redirect
- **Complexity**: Medium
- **Effort**: 2h
- **Tasks**: OIDC login endpoint, state/nonce generation, redirect logic
- **Testing**: Unit test redirect URL construction, state storage

### AC-004: Callback token exchange + validation
- **Complexity**: Complex
- **Effort**: 4h
- **Tasks**: Callback endpoint, code exchange, ID token validation, claim extraction
- **Dependencies**: AC-003, OIDC discovery (AC-010)
- **Risks**: Provider-specific token format quirks
- **Testing**: Mock provider responses, test happy path and error cases

### AC-005: Auto-create user from OIDC
- **Complexity**: Medium
- **Effort**: 2h
- **Tasks**: Create user with Viewer role from OIDC claims, set auth_provider="oidc"
- **Dependencies**: User model (user-management spec), AC-004
- **Testing**: Test new user creation with expected defaults

### AC-006: Auto-link by email match
- **Complexity**: Medium
- **Effort**: 2h
- **Tasks**: Email lookup, link oidc_subject/oidc_issuer to existing user
- **Dependencies**: User model, AC-004
- **Testing**: Test linking, test that role is preserved

### AC-007: OIDC users cannot set local password
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: Guard on password change endpoint
- **Testing**: Test 403 when OIDC user tries password change

### AC-008: Local JWT after OIDC login
- **Complexity**: Simple
- **Effort**: 1h
- **Tasks**: Issue JWT + set session cookie in callback handler
- **Dependencies**: JWT infrastructure (user-management spec)
- **Testing**: Test session cookie is set after callback

### AC-009: OIDC config from env vars
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: Already covered by AC-001 (5 env vars in Settings)
- **Testing**: Covered by AC-001 tests

### AC-010: OIDC Discovery
- **Complexity**: Medium
- **Effort**: 2h
- **Tasks**: Fetch + cache .well-known/openid-configuration, extract endpoints
- **Risks**: Provider down at startup
- **Testing**: Mock discovery response, test caching, test failure handling

### AC-011: Request openid email profile scopes
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: Part of AC-003 redirect URL construction
- **Testing**: Verify scope parameter in redirect URL

### AC-012: Hide local login option
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: Conditional template rendering based on OIDC_HIDE_LOCAL_LOGIN
- **Testing**: Template test with flag on/off

### AC-013: State parameter validation
- **Complexity**: Medium
- **Effort**: 1h
- **Tasks**: Generate + store state, validate on callback, reject mismatches
- **Testing**: Test valid state, invalid state, expired state

### AC-014: Nonce validation
- **Complexity**: Medium
- **Effort**: 1h
- **Tasks**: Generate + store nonce, validate in ID token
- **Testing**: Test nonce match, nonce mismatch

### AC-015: No OIDC button when unconfigured
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: Covered by AC-002 conditional rendering
- **Testing**: Covered by AC-002 tests

### AC-016: Local-only logout
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: Existing logout destroys local session only (no OIDC logout endpoint)
- **Testing**: Verify no redirect to OIDC provider on logout

### AC-017: Update display name/email on login
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: Update user fields from OIDC claims on each login
- **Testing**: Test that changed email/name at provider propagates

## Implementation Phases

### Phase 0: Configuration & Dependencies (0.5 day)

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-001 | Add `authlib` to requirements.txt | 15min | — | — |
| TASK-002 | Add OIDC settings to `app/config.py` (`oidc_issuer_url`, `oidc_client_id`, `oidc_client_secret`, `oidc_provider_name`, `oidc_hide_local_login`) | 30min | — | AC-001, AC-009 |
| TASK-003 | Update `.env.example` with OIDC env vars | 15min | TASK-002 | AC-009 |
| TASK-004 | Add `oidc_subject`, `oidc_issuer`, `auth_provider` columns to User model | 1h | User model exists | AC-005, AC-006 |

**Phase Duration**: 0.5 day
**Blockers**: User model from user-management spec must exist for TASK-004

### Phase 1: OIDC Client Core (1 day)

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-005 | Write failing tests for OIDC discovery, auth flow, callback | 3h | TASK-002 | AC-003, AC-004, AC-010, AC-013, AC-014 |
| TASK-006 | Implement OIDC discovery client (`app/services/oidc.py`) — fetch + cache `.well-known/openid-configuration` | 2h | TASK-005 | AC-010 |
| TASK-007 | Implement state/nonce generation and storage (`app/services/oidc.py`) — in-memory dict with TTL | 1h | TASK-005 | AC-013, AC-014 |
| TASK-008 | Implement `GET /auth/oidc/login` endpoint — build authorize URL, redirect | 1h | TASK-006, TASK-007 | AC-003, AC-011 |
| TASK-009 | Implement `GET /auth/oidc/callback` endpoint — code exchange, ID token validation, claim extraction | 3h | TASK-006, TASK-007, TASK-008 | AC-004, AC-013, AC-014 |

**Phase Duration**: 1 day
**Blockers**: None (OIDC plumbing is independent of User model specifics)

### Phase 2: User Account Integration (1 day)

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-010 | Write failing tests for auto-create, auto-link, JWT issuance | 2h | TASK-004 | AC-005, AC-006, AC-007, AC-008, AC-017 |
| TASK-011 | Implement auto-create user from OIDC claims in callback | 1.5h | TASK-009, TASK-010 | AC-005 |
| TASK-012 | Implement auto-link by email match in callback | 1.5h | TASK-009, TASK-010 | AC-006 |
| TASK-013 | Issue local JWT session after OIDC login (set cookie, redirect) | 1h | TASK-009, TASK-010 | AC-008 |
| TASK-014 | Guard password change for OIDC-only users | 30min | TASK-010 | AC-007 |
| TASK-015 | Update user email/name from claims on each login | 30min | TASK-011, TASK-012 | AC-017 |

**Phase Duration**: 1 day
**Blockers**: TASK-004 (User model columns), Phase 1 complete

### Phase 3: UI & Configuration Endpoint (0.5 day)

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-016 | Write failing tests for login page rendering, config endpoint | 1h | TASK-002 | AC-002, AC-012, AC-015 |
| TASK-017 | Update login template — OIDC button, conditional local form | 1h | TASK-016 | AC-002, AC-012, AC-015 |
| TASK-018 | Implement `GET /api/v1/auth/oidc/config` endpoint | 30min | TASK-016 | AC-002 |
| TASK-019 | Verify logout is local-only (no OIDC provider logout) | 15min | — | AC-016 |

**Phase Duration**: 0.5 day
**Blockers**: Login page must exist (user-management spec)

### Phase 4: Verification & Polish (0.5 day)

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-020 | Write edge case tests (no email claim, duplicate emails, expired state, provider down) | 2h | Phase 1-3 | All edge cases |
| TASK-021 | Run full test suite, fix regressions | 1h | TASK-020 | — |
| TASK-022 | Run ruff check + mypy, fix issues | 30min | TASK-021 | — |
| TASK-023 | Manual end-to-end test with PocketId in Docker | 1h | TASK-021 | All |

**Phase Duration**: 0.5 day

## Effort Summary

| Phase | Estimated Hours | Days (solo) |
|-------|-----------------|-------------|
| Phase 0: Config & Dependencies | 2h | 0.5 |
| Phase 1: OIDC Client Core | 10h | 1 |
| Phase 2: User Integration | 7h | 1 |
| Phase 3: UI & Config Endpoint | 3h | 0.5 |
| Phase 4: Verification & Polish | 4.5h | 0.5 |
| **Total** | **26.5h** | **3.5 days** |

## Dependencies

### External Dependencies
- `authlib` library (OIDC client, JWT validation)
- OIDC provider available for end-to-end testing (PocketId instance)

### Internal Dependencies (Blocking)
- **User Management spec** (`specs/user-management.md`) must be implemented first:
  - User model with username, email, role, password_hash
  - JWT session infrastructure (issue, validate, refresh)
  - Login page template (`/login`)
  - Logout handler
  - Role-based access control middleware

### Internal Dependencies (Non-Blocking)
- Security hardening (rate limiting) — already implemented, will apply to OIDC endpoints automatically

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| User-management spec not yet implemented | High | High | Plan OIDC as a follow-on milestone; Phase 1 (OIDC client) can be built independently |
| PocketId-specific OIDC quirks | Medium | Medium | Test with generic OIDC first (e.g., Keycloak dev instance); PocketId is standards-compliant |
| Token validation edge cases | Medium | Medium | Use authlib's built-in JWT validation; don't roll our own |
| Discovery endpoint caching staleness | Low | Low | Cache with 1h TTL; re-fetch on 401 errors |
| State storage in-memory lost on restart | Low | Low | Acceptable for homelab; users just re-click login button. Could use DB if needed later |

## Testing Strategy

1. **Unit Tests** (Phase 1-3, TDD)
   - OIDC discovery client (mocked HTTP responses)
   - State/nonce generation and validation
   - Authorization URL construction
   - Token exchange (mocked provider)
   - ID token validation (mocked JWKs)
   - Auto-create and auto-link logic
   - Config endpoint response
   - Template rendering (OIDC button presence/absence)

2. **Integration Tests** (Phase 4)
   - Full callback flow with mocked OIDC provider
   - Session cookie set after login
   - Edge cases (no email, duplicate email, expired state)

3. **Manual E2E Test** (Phase 4)
   - Login with PocketId in Docker environment
   - Verify account creation, role assignment, session

4. **Quality Gates**
   - Coverage >= 80% for `app/services/oidc.py` and OIDC endpoints
   - ruff check clean
   - mypy clean
   - All 421+ existing tests still passing

## Deliverables

### Code
- `app/services/oidc.py` — OIDC discovery client, state management, token exchange
- `app/api/endpoints/auth_oidc.py` — Login + callback + config endpoints (or added to existing auth router)
- `app/config.py` — OIDC settings additions
- `app/models/sync_log.py` or `app/models/user.py` — User model OIDC columns
- `app/templates/login.html` — Updated with OIDC button

### Tests
- `tests/test_oidc.py` — All OIDC unit and integration tests

### Configuration
- `.env.example` — Updated with OIDC env vars
- `requirements.txt` — Added authlib

## Success Metrics

- [ ] All 17 acceptance criteria implemented
- [ ] 25+ tests written and passing for OIDC
- [ ] Code coverage >= 80% for new code
- [ ] Zero regressions in existing 421 tests
- [ ] All quality gates passing
- [ ] Manual PocketId login works end-to-end
- [ ] Login page renders correctly in all 3 modes (no OIDC, OIDC + local, OIDC only)

## Plan History

- 2026-02-24: Initial plan created
