# Spec: OIDC Signature Verification

**Version:** 0.1.0
**Created:** 2026-03-15
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Enable JWKS-based signature verification for OIDC ID tokens using `authlib`. Fetch the provider's public keys from their JWKS endpoint (discovered via the OpenID Connect discovery document) and verify the token signature, issuer, and audience before accepting claims. Replaces the current `verify_signature: False` bypass identified as SEC-03 in the codebase review.

### User Story

As a project maintainer, I want OIDC ID tokens cryptographically verified against the provider's published keys, so that forged or tampered tokens cannot be used to authenticate.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | `authlib` is added as a project dependency in `requirements.txt` | Must |
| AC-002 | The OIDC callback fetches the provider's JWKS from the `jwks_uri` in the discovery document | Must |
| AC-003 | ID token signature is verified against the provider's published public keys | Must |
| AC-004 | Token `iss` (issuer) claim is verified against the configured provider issuer | Must |
| AC-005 | Token `aud` (audience) claim is verified against the configured `client_id` | Must |
| AC-006 | Token `exp` (expiry) claim is verified — expired tokens are rejected | Must |
| AC-007 | JWKS responses are cached with a configurable TTL (default 3600 seconds) | Must |
| AC-008 | `OIDC_JWKS_CACHE_TTL_SECONDS` environment variable controls the cache TTL | Must |
| AC-009 | JWKS fetch failure rejects the token, logs the error, and redirects to `/login?error=oidc_failed` | Must |
| AC-010 | Invalid signature rejects the token and redirects to `/login?error=oidc_failed` | Must |
| AC-011 | JWKS fetch timeout is 10 seconds — slow providers do not block the login flow indefinitely | Must |
| AC-012 | Existing OIDC login flow continues to work end-to-end with a valid provider | Must |
| AC-013 | No changes to the OIDC settings UI or database configuration model | Must |
| AC-014 | Error messages shown to users do not leak internal details (JWKS URLs, key IDs, etc.) | Must |

## 3. User Test Cases

### TC-001: Successful OIDC login with signature verification

**Precondition:** OIDC provider configured and enabled, provider has valid JWKS endpoint
**Steps:**
1. User clicks "Login with {provider}" on the login page
2. User authenticates at the provider
3. Provider redirects back with authorization code
4. App exchanges code for tokens
5. App fetches JWKS from provider and verifies ID token signature
6. App creates/links local user and sets session cookie
**Expected Result:** User is logged in and redirected to dashboard
**Screenshot Checkpoint:** N/A (backend-only change)
**Maps to:** TBD

### TC-002: OIDC login fails with tampered token

**Precondition:** OIDC provider configured
**Steps:**
1. User completes OIDC flow
2. ID token is received but signature does not match provider's public keys
**Expected Result:** Login fails, user redirected to `/login?error=oidc_failed`
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-003: JWKS endpoint unreachable

**Precondition:** OIDC provider configured, JWKS endpoint returns error or times out
**Steps:**
1. User completes OIDC authorization
2. App attempts to fetch JWKS from provider
3. JWKS endpoint is unreachable or returns 500
**Expected Result:** Login fails, error logged, user redirected to `/login?error=oidc_failed`
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-004: Cached JWKS avoids redundant fetches

**Precondition:** OIDC provider configured, one successful login already completed
**Steps:**
1. First user logs in via OIDC — JWKS fetched from provider
2. Second user logs in via OIDC within the cache TTL window
**Expected Result:** Second login uses cached JWKS, no additional HTTP request to provider
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-005: Expired token rejected

**Precondition:** OIDC provider configured
**Steps:**
1. User completes OIDC flow
2. ID token has `exp` claim in the past
**Expected Result:** Login fails, user redirected to `/login?error=oidc_failed`
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

## 4. Data Model

No data model changes required. The `OidcConfig` table is unchanged.

New config field in `app/config.py`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `oidc_jwks_cache_ttl_seconds` | int | 3600 | TTL for cached JWKS responses |

## 5. API Contract

Not applicable — no API endpoint changes.

## 6. UI Behavior

Not applicable — no UI changes (AC-013).

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Provider rotates keys (new `kid` not in cache) | Cache miss triggers fresh JWKS fetch |
| Provider JWKS has multiple keys | Match by `kid` from token header |
| Token `kid` header missing | Try all keys in JWKS; reject if none match |
| Token uses unsupported algorithm (e.g., `none`) | Reject — only allow RS256/RS384/RS512/ES256 |
| Discovery document missing `jwks_uri` | Reject token, log error |
| JWKS cache TTL set to 0 | Fetch JWKS on every login (no caching) |
| Concurrent logins during cache refresh | Thread-safe cache access |

## 8. Dependencies

- `authlib` library (new dependency)
- Existing `app/services/oidc.py` module (modified)
- Existing OIDC discovery cache in `app/services/oidc.py`

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-15 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
