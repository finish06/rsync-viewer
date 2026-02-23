# M3 — Reliability

**Goal:** Harden the application with structured logging, comprehensive error handling, and security best practices to prepare for beta maturity promotion
**Status:** PLANNED
**Appetite:** 2 weeks
**Target Maturity:** alpha → beta
**Started:** —
**Completed:** —

## Success Criteria

- [ ] Structured JSON logging with request tracing on all API endpoints
- [ ] Consistent error response format across all endpoints (no stack traces in production)
- [ ] Parser continues on non-fatal errors with line-level error reporting
- [ ] Rate limiting enforced per API key (60/min) and per IP for unauthenticated (20/min)
- [ ] API keys salted and hashed before storage (no plaintext keys in DB)
- [ ] Security headers on all responses (CSP, X-Content-Type-Options, X-Frame-Options, HSTS)
- [ ] All inputs validated with type checking, length limits, and format validation
- [ ] No secrets in codebase — all via environment variables, documented in `.env.example`

## Hill Chart

```
Structured Logging     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Error Handling         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Security Hardening     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Structured Logging | specs/structured-logging.md | SHAPED | JSON logs, request IDs, sensitive data masking, configurable levels |
| Error Handling | specs/error-handling.md | SHAPED | Global exception handler, standardized error JSON, parser resilience |
| Security Hardening | specs/security-hardening.md | SHAPED | Rate limiting, key hashing, input validation, security headers |

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
| — | — | — | Cycles to be planned when milestone starts |

## Retrospective

—
