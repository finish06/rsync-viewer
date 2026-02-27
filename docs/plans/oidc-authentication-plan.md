# Implementation Plan: M7 — OIDC Authentication

**Spec Versions**: oidc-settings.md v0.1.0, oidc-authentication.md v0.2.0
**Created**: 2026-02-24
**Updated**: 2026-02-27
**Team Size**: Solo

## Overview

Add OpenID Connect (OIDC) single sign-on as an optional authentication method. M7 has two specs:

1. **OIDC Settings UI** (`specs/oidc-settings.md`) — Admin configures OIDC provider via Settings page (DB-stored, Fernet-encrypted client secret, test discovery). This must be built first since the auth flow reads config from DB.
2. **OIDC Authentication** (`specs/oidc-authentication.md`) — Authorization Code Flow, user auto-create/link, login page UI, session handling.

## Dependencies — All Satisfied

| Dependency | Status | Notes |
|------------|--------|-------|
| M9 Multi-User (User model, JWT, RBAC, login page) | Complete | PR #15, #17 merged |
| M3 Security Hardening (rate limiting) | Complete | Applies to OIDC endpoints automatically |
| Fernet encryption pattern (SMTP) | Complete | `SmtpConfig` model, `email.py` service |
| `cryptography` package | Installed | Already in requirements.txt |
| `httpx` package | Installed | Already in requirements.txt |

## Objectives

- Admin-configurable OIDC provider via Settings UI (no env vars needed)
- SSO login via any OIDC-compliant provider (PocketId, Authelia, Keycloak, etc.)
- Auto-create and auto-link local accounts from OIDC claims
- Secure flow: state + nonce validation, encrypted client secret at rest
- Backward compatible: no OIDC config = no changes to existing behavior
- `FORCE_LOCAL_LOGIN` env var as safety fallback

## Success Criteria

- All 28 acceptance criteria covered by tests (14 from oidc-settings + 14 active from oidc-authentication)
- Code coverage >= 80% for new OIDC code
- All quality gates passing (ruff, mypy, pytest)
- Zero regressions in existing 594 tests
- OIDC login works end-to-end with PocketId in Docker environment

## Implementation Phases

### Phase 1: Foundation — Config, Model, Encryption (0.5 day)

Establishes the `OidcConfig` DB model and shared encryption infrastructure. Mirrors the `SmtpConfig` pattern.

| Task | Description | ACs (settings) | Files |
|------|-------------|----------------|-------|
| T-01 | Add `force_local_login: bool = False` to `app/config.py` Settings | S-AC-004 | `app/config.py` |
| T-02 | Rename/alias `smtp_encryption_key` → `encryption_key` in Settings (keep backward compat with `SMTP_ENCRYPTION_KEY` env var, also accept `ENCRYPTION_KEY`) | S-AC-005 | `app/config.py` |
| T-03 | Create `app/models/oidc_config.py` — `OidcConfig` SQLModel table (singleton pattern, same as SmtpConfig) | S-AC-001 | `app/models/oidc_config.py` |
| T-04 | Add OIDC encryption helpers to `app/services/oidc.py` — `encrypt_client_secret()` / `decrypt_client_secret()` reusing Fernet from shared encryption key | S-AC-005 | `app/services/oidc.py` |
| T-05 | Add `auth_provider`, `oidc_subject`, `oidc_issuer` columns to User model | A-AC-005, A-AC-006 | `app/models/user.py` |
| T-06 | Import `OidcConfig` in `main.py` for auto table creation | — | `app/main.py` |
| T-07 | Update `.env.example` with `ENCRYPTION_KEY` and `FORCE_LOCAL_LOGIN` | — | `.env.example` |

**Spec traceability:** S = oidc-settings spec, A = oidc-authentication spec

### Phase 2: OIDC Settings Admin UI (1 day)

Admin can configure, test, enable/disable OIDC from the Settings page. Follows the SMTP settings HTMX pattern exactly.

| Task | Description | ACs (settings) | Files |
|------|-------------|----------------|-------|
| T-08 | Write failing tests for OIDC settings CRUD, discovery test, access control | S-AC-001 through S-AC-009 | `tests/test_oidc_settings.py` |
| T-09 | Implement `get_oidc_config(session)` and `save_oidc_config()` service functions (singleton upsert) | S-AC-001, S-AC-012 | `app/services/oidc.py` |
| T-10 | Implement OIDC discovery function — fetch `/.well-known/openid-configuration`, return endpoints | S-AC-007 | `app/services/oidc.py` |
| T-11 | Add HTMX endpoint `GET /htmx/settings/auth` — render OIDC config form (admin only, secret masked) | S-AC-001, S-AC-006, S-AC-008 | `app/main.py` |
| T-12 | Add HTMX endpoint `POST /htmx/settings/auth` — save/update OIDC config (admin only, empty secret preserves existing) | S-AC-001, S-AC-005, S-AC-009, S-AC-011, S-AC-012 | `app/main.py` |
| T-13 | Add HTMX endpoint `POST /htmx/settings/auth/test-discovery` — test discovery against issuer URL | S-AC-007 | `app/main.py` |
| T-14 | Create `app/templates/partials/oidc_settings.html` — form with provider name, issuer URL, client ID, client secret, scopes, toggles, test discovery button, info note about `FORCE_LOCAL_LOGIN` | S-AC-001 through S-AC-006, S-AC-013 | `app/templates/partials/oidc_settings.html` |
| T-15 | Add "Authentication" section to `app/templates/settings.html` — admin-only guard, lazy-load via `hx-get` | S-AC-008 | `app/templates/settings.html` |
| T-16 | Make tests pass (GREEN), then refactor | All settings ACs | All above |

### Phase 3: OIDC Client Core — Auth Code Flow (1 day)

The core OIDC plumbing: state/nonce management, login redirect, callback with token exchange.

| Task | Description | ACs (auth) | Files |
|------|-------------|------------|-------|
| T-17 | Write failing tests for state/nonce generation, auth URL construction, callback token exchange, ID token validation | A-AC-003, A-AC-004, A-AC-010, A-AC-011, A-AC-013, A-AC-014 | `tests/test_oidc_auth.py` |
| T-18 | Implement state/nonce manager in `app/services/oidc.py` — in-memory dict with 10-min TTL, generate/store/validate/cleanup | A-AC-013, A-AC-014 | `app/services/oidc.py` |
| T-19 | Implement `build_authorize_url()` — reads OidcConfig from DB, runs discovery, constructs redirect URL with state/nonce/scopes | A-AC-003, A-AC-010, A-AC-011 | `app/services/oidc.py` |
| T-20 | Implement `exchange_code_for_tokens()` — POST to token endpoint, validate ID token (signature, nonce, iss, aud), extract claims | A-AC-004, A-AC-014 | `app/services/oidc.py` |
| T-21 | Add `GET /auth/oidc/login` endpoint — reads DB config, calls `build_authorize_url()`, returns 302 redirect | A-AC-003 | `app/main.py` or `app/api/endpoints/auth_oidc.py` |
| T-22 | Add `GET /auth/oidc/callback` endpoint — validates state, exchanges code, extracts claims, hands off to user integration (Phase 4) | A-AC-004, A-AC-013 | `app/main.py` or `app/api/endpoints/auth_oidc.py` |
| T-23 | Make tests pass (GREEN), then refactor | — | All above |

**Decision: authlib vs httpx** — Use `httpx` directly (already installed) for discovery fetch and token exchange. Use `PyJWT` (already installed) for ID token validation. This avoids adding `authlib` as a new dependency. If OIDC provider quirks emerge, we can add `authlib` later.

### Phase 4: User Account Integration (0.5 day)

Auto-create/link users from OIDC claims, issue local JWT sessions, guard password changes.

| Task | Description | ACs (auth) | Files |
|------|-------------|------------|-------|
| T-24 | Write failing tests for user auto-create, auto-link, JWT issuance, password guard, claim updates | A-AC-005, A-AC-006, A-AC-007, A-AC-008, A-AC-017 | `tests/test_oidc_auth.py` |
| T-25 | Implement `get_or_create_oidc_user(session, claims)` — lookup by `oidc_subject`, then by email, then create new. Set `auth_provider="oidc"` | A-AC-005, A-AC-006 | `app/services/oidc.py` |
| T-26 | Update claims on each login (email, display name from `preferred_username` or `name`) | A-AC-017 | `app/services/oidc.py` |
| T-27 | Issue local JWT session in callback (access + refresh tokens, set cookies, redirect to dashboard or `return_url`) | A-AC-008 | callback endpoint |
| T-28 | Guard password change/reset for OIDC-only users (`auth_provider == "oidc"` → reject with message) | A-AC-007 | `app/api/endpoints/auth.py`, `app/main.py` |
| T-29 | Make tests pass (GREEN), then refactor | — | All above |

### Phase 5: Login Page UI (0.5 day)

Update the login page to conditionally show the OIDC button and optionally hide local login.

| Task | Description | ACs | Files |
|------|-------------|-----|-------|
| T-30 | Write failing tests for login page rendering in all modes (no OIDC, OIDC+local, OIDC-only, FORCE_LOCAL_LOGIN override) | A-AC-002, A-AC-012, A-AC-015, S-AC-003, S-AC-004 | `tests/test_oidc_auth.py` |
| T-31 | Update `GET /login` route in `main.py` — query `OidcConfig` from DB, pass `oidc_enabled`, `oidc_provider_name`, `hide_local_login` to template. Respect `FORCE_LOCAL_LOGIN` override. | A-AC-001, A-AC-015, S-AC-004 | `app/main.py` |
| T-32 | Update `app/templates/login.html` — add "or" divider + "Login with {provider_name}" button (conditional), hide local form when `hide_local_login` and not `force_local_login` | A-AC-002, A-AC-012 | `app/templates/login.html` |
| T-33 | Verify logout is local-only (existing logout handler doesn't redirect to OIDC provider) | A-AC-016 | `tests/test_oidc_auth.py` |
| T-34 | Make tests pass (GREEN), then refactor | — | All above |

### Phase 6: Edge Cases & Verification (0.5 day)

| Task | Description | ACs | Files |
|------|-------------|-----|-------|
| T-35 | Write edge case tests: no email claim, duplicate emails (sub takes precedence), expired state/nonce, provider unreachable at login time, OIDC disabled with active sessions | Edge cases from both specs | `tests/test_oidc_auth.py` |
| T-36 | Write tests for OIDC settings edge cases: empty secret on edit, discovery fails but save allowed, concurrent admin edits, missing encryption key | S-AC-011, S-AC-012, edge cases | `tests/test_oidc_settings.py` |
| T-37 | Run full test suite — verify zero regressions in existing 594 tests | — | — |
| T-38 | Run quality gates: `ruff check`, `ruff format`, `mypy` | — | — |
| T-39 | Update `.env.example`, `docker-compose.yml` if needed | — | Config files |
| T-40 | Update milestone doc — mark features as VERIFIED/DONE | — | `docs/milestones/M7-oidc-authentication.md` |

## Effort Summary

| Phase | Scope | ACs Covered |
|-------|-------|-------------|
| Phase 1: Foundation | Config, models, encryption | 4 |
| Phase 2: OIDC Settings UI | Admin HTMX UI, CRUD, discovery test | 14 (all settings ACs) |
| Phase 3: Auth Code Flow | State/nonce, login redirect, callback, token exchange | 7 |
| Phase 4: User Integration | Auto-create/link, JWT session, password guard | 5 |
| Phase 5: Login Page UI | OIDC button, hide local form, FORCE_LOCAL_LOGIN | 5 |
| Phase 6: Edge Cases & Verify | Edge cases, quality gates, regressions | All |

## Architecture Decisions

### No `authlib` — use existing deps
`httpx` (already installed) handles OIDC discovery fetch and token exchange HTTP calls. `PyJWT` (already installed) handles ID token validation. `cryptography` (already installed) provides Fernet. This keeps the dependency footprint minimal. If provider-specific quirks require more sophisticated OIDC handling, `authlib` can be added later.

### Shared encryption key
Rename the config setting from `smtp_encryption_key` to `encryption_key` (accept both env var names for backward compat). Both `SmtpConfig` and `OidcConfig` use the same Fernet key. Refactor `app/services/email.py` encryption helpers to a shared location or have `oidc.py` import from email service.

### In-memory state/nonce storage
State and nonce for OIDC CSRF/replay protection are stored in an in-memory dict with 10-minute TTL. Acceptable for a single-instance homelab app. Users simply retry login if state expires (e.g., server restart). No DB table needed for `OidcState`.

### OIDC endpoints in main.py
The browser-facing login flow (`GET /login`, `POST /login`) is already in `main.py`. OIDC login/callback endpoints (`GET /auth/oidc/login`, `GET /auth/oidc/callback`) go alongside them for consistency since they handle browser redirects and cookie setting, not REST API responses.

### Singleton OidcConfig
Same pattern as `SmtpConfig` — integer PK, only one row, upsert on save. Service layer enforces the singleton via `select().limit(1)`.

## File Change Summary

### New Files
| File | Purpose |
|------|---------|
| `app/models/oidc_config.py` | `OidcConfig` SQLModel table |
| `app/services/oidc.py` | Discovery, state/nonce, token exchange, user integration |
| `app/templates/partials/oidc_settings.html` | Admin OIDC config form |
| `tests/test_oidc_settings.py` | OIDC Settings UI tests |
| `tests/test_oidc_auth.py` | OIDC auth flow tests |

### Modified Files
| File | Change |
|------|--------|
| `app/config.py` | Add `encryption_key`, `force_local_login` |
| `app/models/user.py` | Add `auth_provider`, `oidc_subject`, `oidc_issuer` columns |
| `app/main.py` | Import OidcConfig, add HTMX settings endpoints, add OIDC login/callback routes, update `GET /login` context |
| `app/templates/settings.html` | Add "Authentication" section (admin-only) |
| `app/templates/login.html` | Add OIDC button, conditional local form |
| `app/api/endpoints/auth.py` | Guard password reset for OIDC users |
| `app/services/email.py` | Refactor encryption to shared helper (or import from oidc.py) |
| `.env.example` | Add `ENCRYPTION_KEY`, `FORCE_LOCAL_LOGIN` |
| `requirements.txt` | No new deps needed |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PocketId-specific OIDC quirks | Medium | Medium | Test with generic OIDC first; PocketId is standards-compliant |
| ID token validation edge cases (alg, aud, iss) | Medium | Medium | Use PyJWT with explicit algorithm + audience + issuer checks |
| Discovery endpoint caching staleness | Low | Low | Cache with 1h TTL; re-fetch on errors |
| State storage lost on restart | Low | Low | Acceptable for homelab; users retry login |
| Shared encryption key migration | Low | Low | Accept both `SMTP_ENCRYPTION_KEY` and `ENCRYPTION_KEY` env var names |

## Testing Strategy

1. **Unit Tests (TDD, Phases 1-5):** Discovery client (mocked httpx), state/nonce lifecycle, authorize URL construction, token exchange (mocked), ID token validation (mocked JWKs), user auto-create/link, config CRUD, template rendering, access control
2. **Integration Tests (Phase 6):** Full callback flow with mocked provider, session cookie verification, edge cases
3. **Quality Gates:** Coverage >= 80% for new code, ruff clean, mypy clean, 594+ existing tests passing
4. **Manual E2E:** Login with PocketId in Docker, verify account creation, role assignment, session

## Plan History

- 2026-02-24: Initial plan created (spec v0.1.0, env var config)
- 2026-02-27: Major revision — split into 6 phases covering both specs (oidc-settings.md + oidc-authentication.md v0.2.0). Removed `authlib` dependency (use httpx + PyJWT). Updated for DB-based config. All M9 dependencies now satisfied.
