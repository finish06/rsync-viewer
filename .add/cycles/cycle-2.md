# Cycle 2 — M3 Reliability: Logging, Error Handling, Security

**Milestone:** M3 — Reliability
**Maturity:** alpha
**Status:** COMPLETE
**Started:** 2026-02-22
**Completed:** 2026-02-23
**Duration Budget:** 1 week

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| Structured Logging | SHAPED | DONE | Agent-1 | ~2 days | AC-001–AC-012 passing, request_id in all responses |
| Error Handling | SHAPED | DONE | Agent-1 | ~2 days | AC-001–AC-010 passing, consistent error format on all endpoints |
| Security Hardening | SHAPED | DONE | Agent-1 | ~3 days | AC-001–AC-012 passing, rate limiting active, keys hashed, headers set |

## Dependencies & Serialization

```
Structured Logging (Agent-1)
    ↓ (Error Handling depends on logging for request_id and log context)
Error Handling (Agent-1)
    ↓ (Security Hardening depends on both for audit logging and error patterns)
Security Hardening (Agent-1)
```

Single-threaded execution. Features advance sequentially.

## Implementation Order & Plan

### Phase 1: Structured Logging (Days 1-2)

**Spec:** `specs/structured-logging.md` (12 ACs)

TDD cycle:
1. RED: Write tests for JSON log output format, request_id generation, X-Request-ID header, configurable log level, domain event logging, sensitive data masking
2. GREEN: Implement JSON formatter, FastAPI middleware for request tracking (contextvars), domain event loggers, suppress uvicorn access logs
3. REFACTOR: Clean up, ensure no ad-hoc print/logging calls remain
4. VERIFY: Full test suite, lint, mypy

**Key implementation notes:**
- Use `python-json-logger` or custom `logging.Formatter`
- Store `request_id` in `contextvars` for cross-call-stack access
- LOG_LEVEL and LOG_FORMAT env vars
- Suppress/unify uvicorn access logs

### Phase 2: Error Handling (Days 3-4)

**Spec:** `specs/error-handling.md` (10 ACs)

TDD cycle:
1. RED: Write tests for standard error response format, validation error details, global exception handler (no stack traces), database error handling, parser error resilience, error code registry
2. GREEN: Implement ErrorResponse schema, global exception handler middleware, error code registry, date param validation on HTMX endpoints, parser hardening
3. REFACTOR: Replace all ad-hoc HTTPExceptions with standardized error codes
4. VERIFY: Full test suite, lint, mypy, check no stack traces in error responses

**Key implementation notes:**
- ErrorResponse schema: error_code, message, detail, timestamp, path, validation_errors
- Global exception handler catches unhandled exceptions → 500 with INTERNAL_ERROR
- request_id from Phase 1 included in error responses
- Backward compat: keep `detail` field for existing clients

### Phase 3: Security Hardening (Days 4-7)

**Spec:** `specs/security-hardening.md` (12 ACs)

TDD cycle:
1. RED: Write tests for rate limiting (per-key and per-IP), rate limit headers, API key hashing (bcrypt), key migration, input validation, body size limits, security headers, secrets audit, CSRF tokens
2. GREEN: Implement rate limiting (slowapi), key hashing with migration, security headers middleware, input validation, body size limit, CSP in report-only mode
3. REFACTOR: Clean up middleware stack ordering, ensure all env vars documented
4. VERIFY: Full test suite, lint, mypy, manual check of security headers

**Key decisions (from interview):**
- **API key migration:** Hash existing plaintext keys during migration. Existing scripts keep working. New keys shown once at creation, stored hashed.
- **CSP:** Deploy in `Content-Security-Policy-Report-Only` mode first. Log violations. Switch to enforcing after validation in a follow-up.
- **Rate limits:** Generous defaults (60/min auth, 20/min unauth). Configurable via env vars.

**Key implementation notes:**
- Use `slowapi` for FastAPI rate limiting
- Use `bcrypt` for key hashing (or `passlib[bcrypt]`)
- Migration: read existing plaintext key, hash it, store hash + prefix, drop plaintext column
- Security headers via middleware: X-Content-Type-Options, X-Frame-Options, HSTS (optional via env), CSP-Report-Only
- `.env.example` updated with all new env vars

## Validation Criteria

### Per-Item Validation

- **Structured Logging:** AC-001–AC-012 passing. JSON logs on every request. X-Request-ID header present. LOG_LEVEL configurable. Sensitive data never logged.
- **Error Handling:** AC-001–AC-010 passing. All 4xx/5xx responses use ErrorResponse format. No stack traces in production mode. Error codes documented in OpenAPI.
- **Security Hardening:** AC-001–AC-012 passing. Rate limiting returns 429 with Retry-After. Keys hashed in DB. Security headers on all responses. `.env.example` complete.

### Cycle Success Criteria

- [x] All 3 features reach VERIFIED position — all DONE
- [x] All 34 acceptance criteria verified (12 + 10 + 12)
- [x] Full test suite passes (294 tests, up from 237)
- [x] Test coverage >= 80% — 92% achieved
- [x] ruff check clean
- [x] mypy clean
- [x] No secrets in codebase
- [x] `.env.example` documents all environment variables

## Agent Autonomy & Checkpoints

**Mode:** High autonomy (Alpha maturity, human available throughout).

- Agent executes each phase sequentially using TDD
- Agent commits after each completed phase (conventional commits)
- Human reviews at cycle completion (or on request)
- If blocked: agent flags blocker and continues to next phase if possible

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| API key hashing breaks existing keys | Migration hashes existing keys in-place. Test auth with existing key before/after migration. |
| CSP breaks HTMX | Deploy CSP in report-only mode. No blocking. Monitor logs for violations. |
| Rate limiting too aggressive | Generous defaults (60/min). Configurable via env vars. Tests verify limits are correct. |
| Logging overhead | Async-compatible logging. Configurable log levels. Health check at DEBUG to reduce noise. |

## Notes

- This is the beta-gate cycle. Completing M3 unblocks maturity promotion to beta.
- All 3 specs already exist and are approved. No spec work needed.
- Previous cycle (cycle-1) established the TDD workflow at POC maturity. This cycle raises the bar to alpha-level rigor.
- L-004 learning: proactively drop/recreate test DB tables before RED phase to avoid schema mismatch.
- L-005 learning: httpx AsyncClient mock pattern reusable for rate limiting tests if needed.
