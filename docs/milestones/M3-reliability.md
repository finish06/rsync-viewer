# M3 — Reliability

**Goal:** Harden the application with structured logging, comprehensive error handling, and security best practices to prepare for beta maturity promotion
**Status:** COMPLETE
**Appetite:** 2 weeks
**Target Maturity:** alpha → beta
**Started:** 2026-02-22
**Completed:** 2026-02-23

## Success Criteria

- [x] Structured JSON logging with request tracing on all API endpoints
- [x] Consistent error response format across all endpoints (no stack traces in production)
- [x] Parser continues on non-fatal errors with line-level error reporting
- [x] Rate limiting enforced per API key (60/min) and per IP for unauthenticated (20/min)
- [x] API keys salted and hashed before storage (no plaintext keys in DB)
- [x] Security headers on all responses (CSP, X-Content-Type-Options, X-Frame-Options, HSTS)
- [x] All inputs validated with type checking, length limits, and format validation
- [x] No secrets in codebase — all via environment variables, documented in `.env.example`

## Hill Chart

```
Structured Logging     ████████████████████████████████████  DONE
Error Handling         ████████████████████████████████████  DONE
Security Hardening     ████████████████████████████████████  DONE
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Structured Logging | specs/structured-logging.md | DONE | JSON logs, request IDs, sensitive data masking, configurable levels — 15 tests |
| Error Handling | specs/error-handling.md | DONE | Global exception handler, standardized error JSON, parser resilience — 12 tests |
| Security Hardening | specs/security-hardening.md | DONE | Rate limiting, key hashing, input validation, security headers — 30 tests |

## Dependencies

- M1 and M2 must be complete (they are)
- Logging should land first — error handling and security both depend on it for audit trails
- Security hardening key migration requires careful rollout (hash existing plaintext keys)

## Recommended Implementation Order

1. Structured Logging (no dependencies, foundation for the others)
2. Error Handling (uses logging for error tracking)
3. Security Hardening (uses logging for security events, benefits from error handling patterns)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API key hashing migration breaks existing keys | Medium | High | Hash existing keys in migration, test auth flow before/after |
| Rate limiting blocks legitimate heavy use | Low | Medium | Configurable limits via env vars, generous defaults |
| CSP breaks HTMX dynamic content | Medium | Medium | Test CSP policy with all HTMX interactions before enforcing |
| Logging overhead impacts performance | Low | Low | Async logging, configurable log levels |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| cycle-2 | Structured Logging, Error Handling, Security Hardening | COMPLETE | All 3 features SHAPED→DONE. 294 tests, 92% coverage, all quality gates pass. |

## Retrospective

All 3 features implemented via TDD in cycle-2 across v1.2.0–v1.5.0:
- **Structured Logging** (v1.2.0): JSON formatter, request tracking middleware, X-Request-ID, configurable levels, uvicorn suppression. 15 tests.
- **Error Handling** (v1.2.0): Error code registry, ErrorResponse schema, global exception handlers, no stack traces in production. 12 tests.
- **Security Hardening** (v1.5.0): slowapi rate limiting, bcrypt key hashing, security headers middleware, body size limits, CSRF protection, input validation. 30 tests.

Key learnings:
- slowapi `headers_enabled=True` must be set explicitly for X-RateLimit-* headers
- CSRF middleware required updating all existing test fixtures with tokens
- Python venv upgrade from 3.9 to 3.13 was needed for `dict | None` syntax support
