# Spec: Reverse Proxy Support

**Version:** 0.1.0
**Created:** 2026-02-28
**PRD Reference:** docs/prd.md
**Related:** specs/oidc-authentication.md, specs/oidc-settings.md
**Status:** Complete
**Milestone:** M7 — OIDC Authentication

## 1. Overview

Enable the application to correctly resolve its public URL when running behind a reverse proxy (Nginx, Traefik, Caddy, etc.). Without this, internally-generated URLs (e.g., OIDC callback URLs) resolve to the container's internal address instead of the public-facing hostname, breaking integrations that depend on exact URL matching.

### User Story

As an operator deploying rsync-viewer behind a reverse proxy, I want the application to respect forwarded headers (`X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`), so that features like OIDC authentication generate correct callback URLs matching my public domain.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Uvicorn is configured with `--proxy-headers` to read `X-Forwarded-*` headers from the reverse proxy | Must |
| AC-002 | Uvicorn is configured with `--forwarded-allow-ips` to accept forwarded headers from trusted sources | Must |
| AC-003 | `request.base_url` resolves to the public URL (e.g., `https://rsync-viewer.calebdunn.tech`) when behind a proxy | Must |
| AC-004 | OIDC callback URL (`/auth/oidc/callback`) uses the public URL, not the internal container address | Must |
| AC-005 | The production docker-compose file loads `.env` for environment variable injection into the container | Must |
| AC-006 | Application continues to work correctly without a reverse proxy (direct access on `http://localhost:8000`) | Must |

## 3. User Test Cases

### TC-001: OIDC login behind reverse proxy

**Precondition:** App deployed behind reverse proxy with OIDC configured. Public URL is `https://rsync-viewer.calebdunn.tech`.
**Steps:**
1. Navigate to the login page via the public URL
2. Click "Login with [OIDC Provider]"
3. Authenticate with the OIDC provider
4. Provider redirects back to the callback URL
**Expected Result:** Callback URL is `https://rsync-viewer.calebdunn.tech/auth/oidc/callback`. Provider accepts the callback. User is logged in successfully.
**Maps to:** AC-001, AC-002, AC-003, AC-004

### TC-002: Direct access without proxy

**Precondition:** App running locally via `docker-compose up`.
**Steps:**
1. Navigate to `http://localhost:8000`
2. Use the application normally
**Expected Result:** Application works as before. No errors from proxy header handling when headers are absent.
**Maps to:** AC-006

### TC-003: Environment variables loaded from .env in production

**Precondition:** `.env` file exists on the production host with `ENCRYPTION_KEY` set.
**Steps:**
1. Start the app with `docker-compose -f docker-compose.prod.yml up -d`
2. Navigate to Settings > SMTP or Authentication
**Expected Result:** No "ENCRYPTION_KEY is not set" warning. Settings can be saved.
**Maps to:** AC-005

## 4. Data Model

No data model changes. This is an infrastructure/configuration change only.

## 5. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Proxy does not send `X-Forwarded-*` headers | `request.base_url` falls back to the actual host/port (no breakage) |
| Multiple proxies in chain | Uvicorn reads the outermost forwarded values |
| Mixed HTTP/HTTPS (proxy terminates TLS) | `X-Forwarded-Proto: https` ensures `request.base_url` uses `https://` |

## 6. Implementation Notes

### Changes Made

1. **`Dockerfile`** — Added `--proxy-headers` and `--forwarded-allow-ips *` to the uvicorn CMD
2. **`docker-compose.prod.yml`** — Added `env_file: - .env` to the app service

### Reverse Proxy Requirements

The reverse proxy must forward these headers:
- `X-Forwarded-For` — Client IP
- `X-Forwarded-Proto` — Original protocol (http/https)
- `X-Forwarded-Host` — Original hostname

Most reverse proxies (Nginx, Traefik, Caddy) send these by default.
