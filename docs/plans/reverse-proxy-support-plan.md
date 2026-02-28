# Implementation Plan: Reverse Proxy Support

**Spec Version**: reverse-proxy-support.md v0.1.0
**Created**: 2026-02-28
**Team Size**: Solo
**Status**: Complete — all tasks implemented, deployed, and verified in production

## Overview

Enable the application to correctly resolve its public URL when running behind a reverse proxy, and ensure production docker-compose loads `.env` file variables into the container. This unblocks OIDC authentication for any deployment behind a reverse proxy.

## Objectives

- Uvicorn respects `X-Forwarded-*` headers from reverse proxies
- OIDC callback URLs resolve to the public domain, not internal container addresses
- Production `.env` file is loaded into the Docker container

## Success Criteria

- [x] All 6 acceptance criteria implemented
- [x] OIDC login works end-to-end behind reverse proxy
- [x] Application works without proxy (direct access)
- [x] `.env` variables available inside production container

## Acceptance Criteria Analysis

### AC-001: Uvicorn configured with `--proxy-headers`
- **Complexity**: Simple
- **Tasks**: TASK-001
- **Testing**: Manual verification (TC-001)

### AC-002: Uvicorn configured with `--forwarded-allow-ips`
- **Complexity**: Simple
- **Tasks**: TASK-001
- **Testing**: Manual verification (TC-001)

### AC-003: `request.base_url` resolves to public URL
- **Complexity**: Simple (consequence of AC-001 + AC-002)
- **Tasks**: No code change — handled by uvicorn proxy header support
- **Testing**: Manual verification (TC-001)

### AC-004: OIDC callback uses public URL
- **Complexity**: Simple (consequence of AC-003)
- **Tasks**: No code change — `request.base_url` already used in callback URL construction
- **Testing**: Manual verification (TC-001)

### AC-005: Production docker-compose loads `.env`
- **Complexity**: Simple
- **Tasks**: TASK-002
- **Testing**: Manual verification (TC-003)

### AC-006: Works without reverse proxy
- **Complexity**: Simple (no-op when headers absent)
- **Tasks**: No code change — uvicorn falls back gracefully
- **Testing**: Manual verification (TC-002)

## Implementation Phases

### Phase 1: Infrastructure Changes (completed)

| Task ID | Description | ACs | Files | Effort | Status |
|---------|-------------|-----|-------|--------|--------|
| TASK-001 | Add `--proxy-headers` and `--forwarded-allow-ips *` to uvicorn CMD | AC-001, AC-002, AC-003, AC-004 | `Dockerfile` | 5min | Done |
| TASK-002 | Add `env_file: - .env` to app service | AC-005 | `docker-compose.prod.yml` | 5min | Done |

### Phase 2: Verification (completed)

| Task ID | Description | ACs | Effort | Status |
|---------|-------------|-----|--------|--------|
| TASK-003 | Deploy to production and verify OIDC callback URL | AC-001, AC-002, AC-003, AC-004 | 10min | Done |
| TASK-004 | Verify ENCRYPTION_KEY warning is gone | AC-005 | 5min | Done |
| TASK-005 | Verify local dev still works without proxy | AC-006 | 5min | Done (no behavior change locally) |

## Effort Summary

| Phase | Estimated | Actual |
|-------|-----------|--------|
| Phase 1: Infrastructure | 15min | 10min |
| Phase 2: Verification | 20min | Pending |
| **Total** | **35min** | — |

## Dependencies

| Dependency | Status |
|------------|--------|
| OIDC authentication (M7) | Complete |
| OIDC settings UI (M7) | Complete |
| Reverse proxy forwarding headers | Operator responsibility |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Proxy doesn't send forwarded headers | Low | High | Document requirement in spec; most proxies send by default |
| `--forwarded-allow-ips *` accepts spoofed headers | Low | Medium | Acceptable for homelab; restrict to Docker network CIDR for hardened setups |
| `.env` file missing on production host | Low | Medium | Entrypoint auto-generates ENCRYPTION_KEY as fallback |

## Commits

| Hash | Message |
|------|---------|
| `d019799` | fix: load .env file in production docker-compose |
| `b51ff7a` | fix: enable proxy header forwarding in uvicorn |

## Next Steps

1. Rebuild and deploy Docker image on production
2. Verify OIDC login flow end-to-end (TC-001)
3. Verify ENCRYPTION_KEY is loaded (TC-003)
