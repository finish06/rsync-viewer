# Spec: Security Hardening

**Version:** 0.1.0
**Created:** 2026-02-22
**PRD Reference:** docs/prd.md
**Status:** Complete
**Milestone:** M3 — Reliability

## 1. Overview

Harden the application against common web vulnerabilities by implementing rate limiting, improving API key security, adding security headers, strengthening input validation, and ensuring no secrets are exposed in the codebase.

### User Story

As a homelab administrator exposing rsync-viewer to my network, I want the application to be secure against common attacks and API abuse, so that my sync data is protected and the service remains available.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Rate limiting is enforced per API key with configurable limits (default: 60 requests/minute) | Must |
| AC-002 | Unauthenticated endpoints have stricter rate limits (default: 20 requests/minute) | Must |
| AC-003 | Rate limit responses include standard headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset | Must |
| AC-004 | API keys are salted and hashed (bcrypt or argon2) before database storage | Must |
| AC-005 | API key rotation: covered by per-user API key management (`user-management.md`) — users can create multiple keys and delete old ones, no grace period needed | Covered |
| AC-006 | All API inputs are validated with type checking, length limits, and format validation | Must |
| AC-007 | Request body size is limited (default: 10MB) to prevent resource exhaustion | Must |
| AC-008 | Security headers are set on all responses: Content-Security-Policy, X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security | Must |
| AC-009 | No secrets or credentials exist in the codebase (all via environment variables) | Must |
| AC-010 | All required secrets are documented in `.env.example` | Must |
| AC-011 | CSRF protection is implemented for state-changing HTML form submissions | Should |
| AC-011a | CSRF tokens are sent as `X-CSRF-Token` header on all HTMX state-changing requests via double-submit cookie pattern | Must |
| AC-011b | CSRF cookie is not `httponly` so client-side JS can read it for the double-submit header | Must |
| AC-011c | HTMX POST/PUT/DELETE/PATCH to CSRF-protected paths without valid token returns 403 | Must |
| AC-012 | Rate limit exceeded returns HTTP 429 with Retry-After header | Must |

## 3. User Test Cases

### TC-001: Rate limiting enforcement

**Precondition:** App running with rate limiting enabled
**Steps:**
1. Send 60 requests to `/api/v1/sync-logs` within 1 minute with valid API key
2. Send a 61st request
3. Check response headers on successful and rejected requests
**Expected Result:** First 60 requests succeed (200). 61st returns 429 with Retry-After header. All responses include X-RateLimit-* headers showing remaining quota.
**Screenshot Checkpoint:** N/A (API)
**Maps to:** AC-001, AC-003, AC-012

### TC-002: API key hashing

**Precondition:** Application with existing API keys
**Steps:**
1. Create a new API key via the management interface
2. Query the database directly to inspect the stored key value
3. Authenticate using the original plaintext key
**Expected Result:** Database contains only the hashed key (not plaintext). Authentication succeeds with the plaintext key. The hash is not reversible.
**Screenshot Checkpoint:** N/A (security)
**Maps to:** AC-004

### TC-003: Input validation

**Precondition:** App running
**Steps:**
1. POST to `/api/v1/sync-logs` with an excessively large body (> 10MB)
2. POST with invalid field types (string where integer expected)
3. POST with XSS payload in source_name field
**Expected Result:** Oversized body returns 413. Invalid types return 422 with field-level errors. XSS payload is rejected or sanitized, never rendered unescaped.
**Screenshot Checkpoint:** N/A (API)
**Maps to:** AC-006, AC-007

### TC-004: Security headers present

**Precondition:** App running
**Steps:**
1. Make any request to the application
2. Inspect response headers
**Expected Result:** Response includes Content-Security-Policy, X-Content-Type-Options: nosniff, X-Frame-Options: DENY, and Strict-Transport-Security (when HTTPS).
**Screenshot Checkpoint:** N/A (headers)
**Maps to:** AC-008

### TC-005: Secrets audit

**Precondition:** Source code repository
**Steps:**
1. Search codebase for hardcoded secrets, passwords, or API keys
2. Verify `.env.example` documents all required environment variables
**Expected Result:** No hardcoded secrets found. `.env.example` lists every required secret with placeholder values and descriptions.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-009, AC-010

### TC-006: CSRF protection for HTMX requests

**Precondition:** Authenticated user session with CSRF cookie set
**Steps:**
1. Make an HTMX POST to `/htmx/api-keys` without `X-CSRF-Token` header
2. Make an HTMX POST to `/htmx/api-keys` with valid `X-CSRF-Token` header matching cookie
3. Make an HTMX DELETE to `/htmx/api-keys/{id}` without `X-CSRF-Token` header
4. Verify the CSRF cookie is not httponly (JS-readable)
**Expected Result:** Requests without token return 403 CSRF_VALIDATION_FAILED. Requests with valid token succeed. Cookie is accessible to JavaScript.
**Screenshot Checkpoint:** N/A (security)
**Maps to:** AC-011a, AC-011b, AC-011c

## 4. Data Model

### Modified: ApiKey

| Field | Change | Description |
|-------|--------|-------------|
| key_hash | New column | Salted bcrypt/argon2 hash of the API key (replaces plaintext storage) |
| key_prefix | New column | First 8 characters of key for identification (e.g., "rsv_abc1...") |
| expires_at | New column | Optional expiration timestamp |
| key | Removed | Plaintext key no longer stored |

### Migration Notes

- Existing plaintext keys must be hashed during migration
- Key prefix extracted from existing key before hashing
- Original plaintext key is shown once at creation time, then never again

## 5. API Contract

### Rate Limit Headers (all responses)

| Header | Description |
|--------|-------------|
| X-RateLimit-Limit | Max requests per window |
| X-RateLimit-Remaining | Remaining requests in current window |
| X-RateLimit-Reset | Unix timestamp when window resets |

### 429 Too Many Requests

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in {N} seconds.",
    "retry_after": 45
  }
}
```

Headers: `Retry-After: 45`

### POST /api/v1/api-keys (new or modified)

**Description:** Generate a new API key. Returns the plaintext key once.

**Response (201):**
```json
{
  "id": "uuid",
  "key": "rsv_abcdef1234567890...",
  "key_prefix": "rsv_abcd",
  "created_at": "2026-02-22T10:00:00Z",
  "expires_at": null,
  "message": "Save this key now. It cannot be retrieved again."
}
```

### POST /api/v1/api-keys/{id}/rotate

**Description:** Generate a new key while keeping the old one valid for a grace period.

**Request:**
```json
{
  "grace_period_hours": 24
}
```

**Response (200):**
```json
{
  "new_key": "rsv_newkey1234567890...",
  "old_key_expires_at": "2026-02-23T10:00:00Z",
  "message": "Old key remains valid until expiration."
}
```

## 6. Configuration

### New Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| RATE_LIMIT_AUTHENTICATED | 60/minute | Rate limit for authenticated requests |
| RATE_LIMIT_UNAUTHENTICATED | 20/minute | Rate limit for unauthenticated requests |
| MAX_REQUEST_BODY_SIZE | 10485760 | Max request body in bytes (10MB) |
| HSTS_ENABLED | false | Enable Strict-Transport-Security header |
| CSP_POLICY | default-src 'self' | Content-Security-Policy header value |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Rate limit with no API key | Use IP-based rate limiting with stricter limits |
| Multiple API keys from same client | Each key has independent rate limit counter |
| Rate limit window boundary | Clean transition, no requests lost between windows |
| Key rotation during active session | Both old and new keys work during grace period |
| Expired API key used | Return 401 with message indicating key has expired |
| Database migration with existing plaintext keys | Hash all existing keys, preserve functionality |
| CSP blocks legitimate HTMX requests | CSP policy must allow HTMX script-src and connect-src |
| CSRF cookie set as httponly | Cookie must NOT be httponly — JS needs to read it for double-submit header pattern |
| HTMX request missing CSRF header | Middleware returns 403; `htmx:configRequest` listener in base.html auto-attaches token |
| Large file list in rsync output exceeds body limit | Body limit applies to raw request; parsed content can be larger |

## 8. Dependencies

- slowapi library (rate limiting for FastAPI)
- bcrypt or argon2-cffi (key hashing)
- Logging spec (for security event logging)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-22 | 0.1.0 | finish06 | Initial spec from TODO conversion |
