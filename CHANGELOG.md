# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

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
