# M7 — OIDC Authentication

**Goal:** Add OpenID Connect single sign-on as an optional authentication method, supporting PocketId and generic OIDC providers configured via environment variables
**Status:** LATER
**Appetite:** 1 week
**Target Maturity:** beta → ga
**Started:** —
**Completed:** —

## Success Criteria

- [ ] OIDC login available when provider env vars are configured
- [ ] Authorization Code Flow with PKCE/state/nonce validation
- [ ] OIDC Discovery (`.well-known/openid-configuration`) used to resolve endpoints
- [ ] Auto-create local user accounts from OIDC claims (Viewer role default)
- [ ] Auto-link OIDC identity to existing local user by email match
- [ ] Provider-branded login button on login page
- [ ] Option to hide local login form (OIDC-only mode)
- [ ] Local JWT session issued after OIDC login (existing session handling reused)
- [ ] OIDC-only users cannot set local passwords

## Hill Chart

```
OIDC Config & Discovery  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Auth Code Flow           ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
User Account Integration ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Login UI                 ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| OIDC Configuration | specs/oidc-authentication.md | SHAPED | Env var config, discovery endpoint |
| Authorization Code Flow | specs/oidc-authentication.md | SHAPED | Login redirect, callback, token exchange |
| User Auto-Create/Link | specs/oidc-authentication.md | SHAPED | Create or link local accounts from OIDC claims |
| Login UI Integration | specs/oidc-authentication.md | SHAPED | Provider-branded button, hide local form option |

## Dependencies

- M9 (Multi-User) provides the User model, JWT session infrastructure, login page, and RBAC that OIDC extends
- M3 (Reliability) must be complete — security hardening provides rate limiting on auth endpoints
- External: `authlib` library for OIDC client
- External: OIDC provider (PocketId or generic) available for testing

## Recommended Implementation Order

1. OIDC config settings + authlib dependency (foundation)
2. OIDC discovery client (fetch + cache provider endpoints)
3. State/nonce management (CSRF + replay protection)
4. Login + callback endpoints (Authorization Code Flow)
5. User auto-create and auto-link logic
6. Login page UI (OIDC button, hide local form option)
7. Edge cases and verification

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| M9 (Multi-User) not yet implemented | High | High | OIDC client core can be built independently; user integration waits |
| PocketId-specific OIDC quirks | Medium | Medium | Test with generic OIDC first; PocketId is standards-compliant |
| Token validation edge cases | Medium | Medium | Use authlib's built-in JWT validation |
| In-memory state storage lost on restart | Low | Low | Acceptable for homelab; users just retry login |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| — | — | — | Cycles to be planned when milestone starts |

## Retrospective

—
