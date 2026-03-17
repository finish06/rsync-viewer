# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Added

- Persist user theme preferences in database (server-side injection, fire-and-forget PATCH)
- Add `/version` endpoint with build and runtime metadata
- Add pip-audit security scanning to CI pipeline
- Externalize app version via `APP_VERSION` env var

### Changed

- Extract shared helpers and eliminate code duplication (P3 refactoring)

### Fixed

- Prevent grep exit code 1 from failing CI auto-tag step
- Security and performance review findings (P0+P1)
- Resolve verify findings — CVEs, mypy errors, coverage gaps, stale branches
- Skip CI auto-tag when HEAD already has a version tag
- CSRF double-submit cookie pattern for HTMX requests

### Documentation

- Add docs manifest with full codebase discovery (80 routes, 14 models, 12 services)
- Add 7 new sequence diagrams (analytics, webhooks, settings, auth, stale detection, preferences, monitoring)
- Sync README features list and test stats (950 tests, 95% coverage)
- Update architecture docs and CLAUDE.md

## [2.3.1] - 2026-03-15

### Security

- **Fix open redirect** on post-login `return_url` — validate relative paths only
- **Wire up rate limiting** on register, login, and password-reset endpoints (SlowAPI)
- **Escape OIDC discovery output** — prevent reflected XSS via `html.escape()`
- **Startup guard** — block production startup with default `secret_key="change-me"`
- **Secure cookie flag** — `access_token` cookie sets `secure=True` in non-debug mode
- **Expand CSRF protection** to `/htmx/synthetic-settings` and `/htmx/monitoring-setup`

### Fixed

- Offload bcrypt API key verification to thread pool (`run_in_executor`) — prevents event loop blocking
- Replace per-row DELETE with bulk DELETE in synthetic check result pruning
- Cap `load_all` dashboard query from 10,000 to 500 rows
- Replace hardcoded `http://127.0.0.1:8000` with configurable `base_url` setting
- Replace `__import__("datetime")` anti-pattern with proper import in retention service

### Changed

- Extract `is_last_admin()` service function (was duplicated 4x across admin routes)
- Replace 8 bare `"admin"` string literals with `ROLE_ADMIN` constant
- Extract `_extract_discord_options()` helper (deduplicates webhook create/update)
- Extract `PASSWORD_RESET_TOKEN_EXPIRY` constant shared across auth endpoints
- Deduplicate API key list query in revoke handler
- Move rate limiter to shared `app/rate_limit.py` module

## [2.3.0] - 2026-03-14

### Security

- **Upgrade PyJWT** to >=2.12.0 — fixes CVE-2026-32597
- **Upgrade pip** to 26.0.1 — fixes CVE-2026-1703

### Fixed

- Fix 4 mypy `no-any-return` errors in `email.py` and `oidc.py` — add explicit `str()` casts for Fernet encrypt/decrypt returns

### Added

- **Sequence diagrams** (`docs/sequence-diagram.md`) — 12 Mermaid diagrams covering ingestion, auth, OIDC, webhooks, synthetic monitoring, admin, health, metrics, retention
- **62 new tests** for HTMX routes — 18 for `/htmx/api-keys` (59% → 93% coverage), 44 for `/htmx/webhooks` (75% → 99% coverage)
- Expanded `CLAUDE.md` key directories from ~10 to 40+ entries with all endpoints, routes, models, services, middleware
- Updated `docs/architecture.md` with auth, RBAC, OIDC, synthetic monitoring, HTMX routes, full 7-layer middleware stack

### Changed

- Overall test coverage 93% → 95% (923 tests total)
- Cleaned up 10 stale merged remote branches

## [2.2.1] - 2026-03-14

### Fixed

- **CSRF validation failed on all HTMX requests** — CSRF cookie was `httponly=True`, preventing JavaScript from reading it to send as the `X-CSRF-Token` header. All HTMX state-changing requests (API keys, webhooks, SMTP settings, admin users) returned 403 in production.
- Add `htmx:configRequest` listener in `base.html` to automatically attach CSRF token header on every HTMX request

### Added

- AC-011a/b/c acceptance criteria in security-hardening spec for HTMX CSRF double-submit cookie pattern
- 7 regression tests covering CSRF header validation, cookie httponly flag, and token mismatch scenarios

## [2.1.0] - 2026-03-05

### Added

- **Synthetic monitoring v0.2.0** — DB-backed config, runtime enable/disable, history dashboard
- **Synthetic source filter** — hide `__synthetic_check` from default views and API responses (tri-state filter: hide/show/only)
- Align analytics filter controls with sync logs view layout (quick-select, dropdowns, conditional date pickers)
- Changelog presentation — color-coded section badges, inline markdown, CSS accordion, pagination
- Date-range quick-select buttons for Analytics and Notifications tabs
- Beta branch CI workflow and auto-version tagging on main
- Standalone smoke test workflow with manual dispatch (`gh workflow run smoke-test.yml`)

### Fixed

- Include start_time and end_time in synthetic check POST payload
- OIDC settings info boxes render correctly in dark mode
- Smoke test CI: use correct docker-compose.yml (app + db, not dev-only)
- Smoke test CI: add app healthcheck and wait-for-ready retry loop
- Isolate smoke tests from root conftest with `-c /dev/null --noconftest`
- Quote YAML value containing colon in CI smoke test step

### Documentation

- Mark AC-005 (API key rotation) as covered by per-user API key management spec
- Mark synthetic source filter spec as complete (v1.0.0)
- Add and update specs for UI polish features

## [2.0.0] - 2026-03-03

### GA Promotion

Rsync Log Viewer promoted to **General Availability** (GA) maturity.

All milestones (M1–M11) complete. 12 days production stability since beta promotion (2026-02-24). v2.0.0 marks the project as production-grade for homelab deployment.

### Added

- **Smoke test suite** (`tests/smoke/test_smoke.py`): 7 standalone tests for deployment verification — health, metrics, login, docs, security headers, auth, rate limiting
- **PR template** (`.github/PULL_REQUEST_TEMPLATE.md`): Summary, spec reference, quality and TDD checklists
- **Project glossary** (`docs/glossary.md`): 15 domain terms defined (Sync Log, Source Name, Exit Code, etc.)
- **Service Level Targets** in PRD: availability 99%, API P95 <500ms, ingestion 99.9%
- **SLA configuration** in `.add/config.json` for monitoring thresholds
- **Smoke test CI job**: runs after build-push on main branch merges

### Changed

- Docker image tag strategy: `latest` + `sha-{SHA}` on main merge, version tag on `v*` tag push (replaces `beta` tag)
- `docker-compose.prod.yml` image tag changed from `beta` to `latest`
- CI workflow triggers on `v*` tags for versioned image pushes
- Test runner ignores `tests/smoke/` directory (smoke tests run separately)
- Maturity promoted from `beta` to `ga` in `.add/config.json`
- Version bumped from 1.11.0 to 2.0.0

## [1.11.0] - 2026-03-01

### Added

- **Alembic database migrations:**
  - Replace `SQLModel.metadata.create_all()` with versioned Alembic migrations
  - Baseline migration covering all 12 tables with indexes and constraints
  - Auto-migrate on container startup via `entrypoint.sh`
  - Dockerfile updated to include `alembic.ini` and `alembic/` directory
- **Rsync client Docker Compose examples (M10):**
  - Pre-built rsync client container with cron scheduling and SSH key support
  - Docker Compose examples for easy deployment alongside the hub
- **E2E test pipeline:**
  - Full integration test: rsync client → SSH transfer → POST to hub → verify parsed log
  - 5-service Docker Compose stack (db, app, ssh-keygen, rsync-server, rsync-client)
- Grafana dashboard datasource variable (`DS_PROMETHEUS`) on all panels and queries
- Project icon — neon wireframe gear with infinity symbol

### Changed

- **Codebase hardening refactor:**
  - Split `main.py` route handlers into domain-specific modules (`app/routes/`)
  - Extract shared services: sync filters, registration, webhook test, JWT decode, API key lookup
  - Phase 1 quick wins: dead code removal, import cleanup, CSRF consolidation
- 73 new unit tests for extracted services and helpers
- Coverage tests for deps, email, notification schema, and middleware

### Fixed

- PR #21 review findings: registration docstring, dead sentinel removal, Discord color constant, admin guard comment
- Mypy type errors in route modules and sync_filters

### Documentation

- Comprehensive Development section added to README
- Alembic migrations and user preferences specs and plans
- M10/M12 merged into unified rsync client milestone spec

## [1.10.0] - 2026-02-28

### Added

- **OIDC authentication (M7):**
  - OpenID Connect SSO via any OIDC-compliant provider (PocketId, Authelia, Keycloak, etc.)
  - Admin-configurable OIDC settings UI (issuer URL, client ID, client secret, provider name)
  - OIDC discovery test button to verify provider configuration
  - Auto-create and auto-link local accounts from OIDC claims
  - State + nonce validation for secure authorization code flow
  - "Hide Local Login" mode with `FORCE_LOCAL_LOGIN` env var safety fallback
  - Client secret encrypted at rest with Fernet symmetric encryption
  - OIDC callback URL displayed in settings UI for easy provider configuration
- **Reverse proxy support:**
  - Uvicorn proxy header forwarding (`--proxy-headers`, `--forwarded-allow-ips`)
  - Production docker-compose loads `.env` file into container
- Auto-generate ENCRYPTION_KEY in Docker entrypoint if not provided
- Fallback for legacy API keys without user_id (treated as operator-level)

### Fixed

- OIDC callback URL resolves to public domain when behind reverse proxy
- Production container reads ENCRYPTION_KEY from `.env` file
- API key prefix filter handles legacy keys without `rsv_` prefix
- Mypy type errors in OIDC service resolved
- Auth middleware, email mock, and OIDC edge case test failures resolved
- Flaky metrics perf test threshold relaxed from 100ms to 200ms
- Mobile card layout CSS specificity conflict on desktop
- CSS cache-busting added for static assets

### Changed

- Optimized API key lookup, SMTP sending (async), changelog caching, and retention queries

### Documentation

- Update L-011 to critical — production DB migration is mandatory after model changes

## [1.9.0] - 2026-02-27

### Added

- **SMTP email configuration (M11):**
  - Admin Settings UI for configuring SMTP server (host, port, encryption, credentials)
  - Send test email button to verify SMTP configuration
  - SMTP credentials encrypted at rest with Fernet symmetric encryption
  - Singleton SMTP config model (one config per instance)
- **Registration toggle:**
  - `REGISTRATION_ENABLED` environment variable to disable new user signups
  - GET /register shows "disabled" message when registration is off
  - POST /register and POST /api/v1/auth/register return 403 when disabled
- **Sync logs UI improvements:**
  - Quick-select date range buttons (Today, 7d, 30d, 90d) integrated into filter box
  - Mobile-responsive card layout for sync logs below 768px
- **Dev seed data:**
  - `python -m scripts.seed` command to populate database with sample data
  - Seeds admin/viewer users, API key, sync logs, webhooks, and notifications
- 28 new tests for SMTP settings, registration toggle, email service, and password reset
- 596 total tests passing with 83% coverage

### Fixed

- **Password reset token no longer exposed in production:** reset token only returned in API response when `DEBUG=true` (security fix)
- SMTP test email error handler shows generic message instead of raw exception details
- SmtpConfig model explicitly registered in test conftest for reliable table creation

### Changed

- M11 (Polish & Infrastructure) milestone marked COMPLETE (6/6 success criteria met)

## [1.8.0] - 2026-02-26

### Added

- **Multi-user authentication system (M9):**
  - User model with UUID primary keys, bcrypt password hashing, and role field
  - JWT authentication with access/refresh token rotation and cookie-based sessions
  - Login and registration UI pages with dark mode support
  - RBAC with three roles: admin, operator, viewer
  - Protected routes with role-based access control middleware
  - Dual authentication: JWT cookies for browser, API keys for scripts
  - Per-user API key management with optional role scoping
  - API key CRUD UI in settings page with HTMX interactions
- **Admin user management (AC-006):**
  - Admin API endpoints: list users, change roles, enable/disable, delete
  - Admin UI page at `/admin/users` with HTMX-powered table
  - Safety checks: cannot demote/delete self, last-admin protection
- **Password reset (AC-013):**
  - Self-service flow: request reset via email, confirm with token
  - Admin-initiated password reset for any user
  - Console-logged tokens for MVP (no SMTP)
  - Forgot password and reset password UI pages
  - Token single-use enforcement and 1-hour expiry
- **Session timeout handling (AC-016):**
  - HTMX requests with expired JWT return 401 (instead of 302 redirect)
  - Login page includes forgot password link
- 33 new tests for admin management, password reset, and session timeout
- 568 total tests passing with 90%+ coverage

### Changed

- Auth redirect middleware: public path allowlist expanded for forgot/reset password
- Auth redirect middleware: HTMX requests get 401 JSON response instead of redirect

### Fixed

- Ruff formatting applied to 6 files

### Documentation

- Cycle 9-12 plans and status tracking for M9 milestone phases

## [1.7.0] - 2026-02-24

### Added

- Development & deployment setup guide (`docs/setup.md`)
- Environment variables reference with all 19 config vars (`docs/environment-variables.md`)
- Architecture diagram with Mermaid and data flow documentation (`docs/architecture.md`)
- Database schema documentation for all 6 tables (`docs/database-schema.md`)
- Rsync log ingestion guide with curl and bash script examples (`docs/ingestion-guide.md`)
- Troubleshooting guide covering database, Docker, and API issues (`docs/troubleshooting.md`)
- Grafana sync overview dashboard template (`grafana/sync-overview.json`)
- Grafana API performance dashboard template (`grafana/api-performance.json`)
- 27 automated tests verifying documentation completeness and dashboard validity

### Fixed

- Isolate Playwright e2e tests from pytest-asyncio unit tests to prevent event loop contamination
- Mount `docs/` and `grafana/` directories in CI test container

### Changed

- M6 Observability milestone marked COMPLETE (8/8 success criteria met)

## [1.6.0] - 2026-02-23

### Added

- Prometheus `/metrics` endpoint with sync, API, and application health metrics
- Sync metrics: totals, duration histogram, files/bytes counters (per source)
- API metrics: request totals and duration histogram (per endpoint/method)
- Application health metrics: version info gauge
- Data retention service with configurable auto-cleanup (`DATA_RETENTION_DAYS`)
- Background retention task with FK cascade deletion order
- 26 metrics and retention tests

## [1.5.0] - 2026-02-23

### Added

- Rate limiting with slowapi (60/min auth, 20/min unauth) with X-RateLimit-* headers
- Security headers middleware (X-Content-Type-Options, X-Frame-Options, CSP report-only)
- Request body size limit middleware (10MB default, returns 413)
- CSRF protection for HTMX form submissions (token-based validation)
- API key hashing with bcrypt (replaces SHA-256)
- API key rotation support (key_prefix, expires_at fields on ApiKey model)
- Input validation: raw_content max_length (10MB), source_name min_length (1)
- 30 security hardening tests covering all 12 acceptance criteria
- Architecture mermaid diagram (docs/architecture.mmd)
- Deprecation cleanup spec for future work

### Changed

- Upgrade venv from Python 3.9 to Python 3.13
- ApiKey.key_hash max_length increased from 64 to 128 (bcrypt support)
- Test client fixture now includes CSRF token cookie/header

### Documentation

- Add security hardening spec (specs/security-hardening.md)
- Add deprecation cleanup spec (specs/deprecation-cleanup.md)
- Define M3-M8 milestone specs and roadmap

## [1.4.0] - 2026-02-22

### Added

- Add notification history dashboard with HTMX tab, filters, and pagination
- Add API key debounce spec and tests (10 tests verifying existing implementation)
- Add notification history spec and implementation plan

### Fixed

- Resolve all mypy type errors across codebase (21 errors fixed)
- Fix ruff lint error (unused variable) and format 15 files

### Documentation

- Mark M2 (Notifications) milestone as COMPLETE (6/6 criteria met)
- Mark M5 (API Performance) milestone as COMPLETE (5/5 criteria met)
- Update PRD roadmap — M1, M2, M5 complete; maturity promoted to Alpha

## [1.3.0] - 2026-02-22

### Added

- Add failure detection with exit code tracking and stale sync monitoring
- Add webhook notification service with retry logic and auto-disable
- Add Discord integration with rich embeds, source filters, and rate limiting
- Add webhook settings UI with HTMX CRUD (add/edit/delete/toggle/test)
- Add webhook settings UI tests (21 tests covering AC-007)
- Add monitor last_sync_at update integration test

### Changed

- Debounce API key writes, fix stale checker N+1 queries, add database indexes
- Add webhook.enabled index and reduce DB commits in HTMX handlers
- Fix N+1 queries and reduce excessive DB commits in Discord integration
- Clean up Discord integration code and remove unused imports

### Fixed

- Add python-multipart dependency for form parsing
- Log unhandled exceptions in global error handler

## [1.2.0] - 2026-02-20

### Added

- Add average transfer rate column and detail field
- Add date range quick select to dashboard
- Add structured JSON logging with request tracking
- Add structured error handling with error codes

### Documentation

- Add error handling and structured logging specs and plans
- Add versioned changelog sections for 1.0.0 and 1.1.0

## [1.1.0] - 2026-02-19

### Added

- Add dark mode with light/dark/system theme toggle

### Documentation

- Add MIT license

## [1.0.0] - 2026-01-26

### Added

- Initial project files
- REST API for rsync log ingestion and querying
- Rsync output parser with support for all byte units
- Dashboard with HTMX-powered sync table and charts
- API key authentication
- Docker Compose development environment

### Documentation

- Add README with project documentation
- Add prerequisites and contributing sections to README
- Enhance API documentation for OpenAPI/Swagger
