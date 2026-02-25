# Rsync Log Viewer — Product Requirements Document

**Version:** 0.2.0
**Created:** 2026-02-19
**Author:** finish06
**Status:** Draft

## 1. Problem Statement

Rsync is widely used for file synchronization across servers and devices, but its output is ephemeral — once a sync completes, the transfer statistics, file lists, and error information are lost unless manually captured. For users managing multiple rsync jobs across a homelab or small infrastructure, there is no simple way to aggregate, search, and visualize sync history over time.

Rsync Log Viewer solves this by providing a centralized web dashboard that collects rsync output via API, automatically parses transfer statistics, and presents rich visualizations of sync activity — enabling users to track backup health, detect failed syncs, and understand transfer patterns.

## 2. Target Users

- **Primary:** Homelab administrators managing multiple rsync backup jobs across servers
- **Secondary:** Small teams or households with automated sync scripts
- **Persona:** Technical user comfortable with Docker, cron jobs, and shell scripting; wants a "set and forget" monitoring dashboard for rsync activity

## 3. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Reliable log capture | 100% of submitted logs parsed without data loss | API success rate, parsing error count |
| Webhook notifications | Failed syncs trigger HA/Discord alerts within 60s | Notification delivery latency |
| Dashboard usability | All sync history viewable with filtering in < 3 clicks | Manual UX validation |
| Visualization coverage | Duration, file count, and bytes trends visible per source | Chart feature completeness |

## 4. Scope

### In Scope (MVP)

- REST API endpoint for receiving rsync output logs (with API key auth)
- Automatic parsing of rsync transfer statistics (bytes, speed, file counts, speedup)
- Dry run detection and filtering
- Web dashboard with interactive table (filtering by source, date, sync type)
- Visualizations: sync duration, file counts, bytes transferred over time
- Docker Compose deployment for homelab
- **Webhook notifications for failed syncs** (Home Assistant, Discord)

### Out of Scope (MVP)

- Mobile-native app
- Cloud-hosted SaaS deployment

### Future Scope (Post-MVP)

- OIDC single sign-on authentication (M7)
- Scheduled rsync execution and sync management (M8)
- Multi-user authentication and role-based access (M9)
- Prometheus metrics export and Grafana dashboards (M6)

## 5. Architecture

### Tech Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Language (backend) | Python | 3.11+ | Primary application language |
| Backend Framework | FastAPI | latest | Async web framework with OpenAPI support |
| ORM | SQLModel | latest | SQLAlchemy + Pydantic integration |
| Database | PostgreSQL | 16+ | JSONB for file lists, indexed queries |
| Frontend | Jinja2 + HTMX | latest | Server-rendered with dynamic updates |
| Containerization | Docker + Docker Compose | latest | Development and production deployment |

### Infrastructure

| Component | Choice | Notes |
|-----------|--------|-------|
| Git Host | GitHub | github.com/finish06/rsync-viewer |
| Cloud Provider | Self-hosted | Homelab deployment |
| CI/CD | GitHub Actions | To be scaffolded |
| Containers | Docker Compose | Dev, test, and production configs |
| IaC | None | Single-server homelab deployment |

### Environment Strategy

| Environment | Purpose | URL | Deploy Trigger |
|-------------|---------|-----|----------------|
| Local | Development & testing | http://localhost:8000 | Manual (docker-compose up) |
| Production | Live homelab instance | TBD (homelab IP/domain) | Merge to main |

**Environment Tier:** 2 (local + production)

Production deployment is to a self-hosted homelab server. No staging environment — changes are validated locally with Docker before deploying to production.

## 6. Milestones & Roadmap

### Current Maturity: Alpha

### Roadmap

| Milestone | Goal | Target Maturity | Status | Success Criteria |
|-----------|------|-----------------|--------|------------------|
| M1: Foundation | Stabilize existing features, add CI/CD | poc → alpha | COMPLETE | CI pipeline, 80% coverage, conventional commits |
| M2: Notifications | Webhook alerts for failed syncs | alpha | COMPLETE | HA/Discord webhooks, settings UI, notification history |
| M3: Reliability | Error handling, logging, security hardening | alpha → beta | COMPLETE | Structured logging, input validation, rate limiting, key hashing |
| M4: Analytics & Performance | Trend analysis, dashboards, query optimization | beta | NEXT | Statistics API, Chart.js charts, cursor pagination, DB indexes |
| M5: API Performance | Debounce API key `last_used_at` writes | alpha | COMPLETE | Configurable debounce, zero regression, fewer DB writes |
| M6: Observability | Prometheus metrics, Grafana dashboards, project docs | beta | NEXT | /metrics endpoint, Grafana templates, setup/architecture docs |
| M7: OIDC Authentication | OpenID Connect single sign-on via PocketId or generic provider | beta → ga | LATER | OIDC login, auto-create/link users, provider-branded UI |
| M8: Sync Management | On-demand sync triggering, cron scheduling, real-time progress | beta → ga | LATER | Run Now button, cron schedules, WebSocket progress, retry |
| M9: Multi-User | User accounts, JWT auth, role-based access control | beta → ga | LATER | Registration/login, Admin/Operator/Viewer roles, per-user API keys |

### Dependency Chain

```
M3 (Reliability) → M4 (Analytics & Performance) → M6 (Observability)
                 ↘ M9 (Multi-User) → M7 (OIDC Authentication)
                 ↘ M8 (Sync Management)
```

M3 is the gate to beta promotion. M4 and M6 can partially overlap. M7 (OIDC) depends on M9 (Multi-User) for the User model and JWT infrastructure. M8 is independent.

### Milestone Detail

#### M1: Foundation [COMPLETE]
**Goal:** Establish CI/CD pipeline, improve test coverage, adopt conventional commits
**Appetite:** 1-2 weeks
**Target maturity:** alpha
**Features:**
- GitHub Actions CI pipeline (lint, test, coverage)
- Comprehensive error handling with consistent response format
- Structured logging with request/response tracking
- Test coverage to 80%+
**Success criteria:**
- [x] GitHub Actions runs on every PR
- [x] Test coverage >= 80%
- [x] All existing tests pass in CI
- [x] Conventional commit format adopted

#### M2: Notifications [COMPLETE]
**Goal:** Alert users when syncs fail via webhooks, with Discord support and settings UI
**Appetite:** 1 week
**Target maturity:** alpha
**Features:**
- Failure detection (exit code + stale sync monitoring)
- Webhook notification service (retry, auto-disable, notification log)
- Discord webhook integration (embeds, source filters, rate limiting)
- Webhook settings UI (full CRUD + toggle + test button)
- Notification history dashboard (HTMX tab with filters + pagination)
**Success criteria:**
- [x] Failed sync triggers webhook within 60 seconds
- [x] Discord integration tested and working (26 tests)
- [x] Webhook settings UI at /settings (21 tests)
- [x] Notification history viewable in dashboard (17 tests)

#### M5: API Performance [COMPLETE]
**Goal:** Reduce unnecessary DB writes by debouncing API key `last_used_at` updates
**Appetite:** 2-3 days
**Target maturity:** alpha
**Features:**
- Time-based debounce in `verify_api_key` (5-minute window)
**Success criteria:**
- [x] Debounce prevents writes within 5-minute window (10 tests)
- [x] No regression in API key authentication behavior

#### M3: Reliability [COMPLETE]
**Goal:** Harden the app with structured logging, error handling, and security best practices
**Appetite:** 2 weeks
**Target maturity:** alpha → beta
**Specs:** structured-logging, error-handling, security-hardening
**Completed:** 2026-02-23 (v1.2.0–v1.5.0)
**Features:**
- Structured JSON logging with request IDs and sensitive data masking
- Global exception handler with consistent error response format
- Rate limiting per API key and per IP
- API key hashing (salted bcrypt, no plaintext storage)
- Security headers (CSP, X-Content-Type-Options, X-Frame-Options, HSTS)
- Input validation with type checking and length limits
- CSRF protection for HTMX form submissions
**Success criteria:**
- [x] All API endpoints log requests/responses in structured JSON
- [x] All errors return consistent format, no stack traces in production
- [x] Rate limiting enforced (60/min authenticated, 20/min unauthenticated)
- [x] API keys hashed in DB, no plaintext
- [x] Security headers on all responses
- [x] No secrets in codebase

#### M4: Analytics & Performance [NEXT]
**Goal:** Trend analysis, statistics, data export, interactive charts — with DB optimizations
**Appetite:** 2 weeks
**Target maturity:** beta
**Specs:** analytics, performance
**Features:**
- Statistics API (daily/weekly/monthly summaries, per-source breakdowns)
- CSV and JSON data export with date range and source filters
- Interactive Chart.js dashboards (duration, file count, bytes trends)
- Database indexes on frequently queried columns
- Cursor-based pagination (replaces offset pagination)
- N+1 query elimination and connection pool tuning
**Success criteria:**
- [x] Statistics API returns aggregated data for custom date ranges
- [x] CSV/JSON export works with filters
- [x] Dashboard has interactive charts with date range selector
- [x] API responses < 200ms with 10,000+ records (benchmarked at 10,501 records)
- [x] Cursor pagination on sync logs endpoint

#### M6: Observability [NEXT]
**Goal:** Prometheus metrics for monitoring, Grafana dashboards, comprehensive project docs
**Appetite:** 1 week
**Target maturity:** beta
**Specs:** metrics-export, documentation
**Features:**
- Prometheus /metrics endpoint (sync, API, and health metrics)
- Grafana dashboard JSON templates
- Configurable data retention with automatic cleanup
- Setup guide, architecture docs, env var reference, troubleshooting guide
**Success criteria:**
- [ ] /metrics returns valid Prometheus format
- [ ] Grafana dashboards visualize sync and API metrics
- [ ] New developers can deploy using only documentation
- [ ] All environment variables documented

#### M7: OIDC Authentication [LATER]
**Goal:** Add OpenID Connect SSO as optional auth method
**Appetite:** 1 week
**Target maturity:** beta → ga
**Specs:** oidc-authentication
**Features:**
- OIDC Authorization Code Flow with state/nonce validation
- OIDC Discovery (`.well-known/openid-configuration`)
- Auto-create/link local accounts from OIDC claims
- Provider-branded login button, optional OIDC-only mode
**Success criteria:**
- [ ] OIDC login works with PocketId and generic providers
- [ ] New users auto-created with Viewer role
- [ ] Existing users auto-linked by email
- [ ] Local JWT session issued after OIDC login

#### M8: Sync Management [LATER]
**Goal:** Transform viewer into active sync management platform
**Appetite:** 3 weeks
**Target maturity:** beta → ga
**Specs:** sync-scheduling
**Features:**
- Sync configuration CRUD (source, destination, flags, SSH key)
- On-demand sync triggering with dry-run mode
- Cron-based scheduling with builder UI
- Real-time progress via WebSocket/SSE
- Retry with exponential backoff, cancellation support
**Success criteria:**
- [ ] "Run Now" triggers sync and captures output as sync log
- [ ] Cron schedules execute automatically
- [ ] Real-time progress updates in UI
- [ ] Failed syncs retry with backoff
- [ ] No command injection vulnerabilities

#### M9: Multi-User [LATER]
**Goal:** Multi-user support with authentication and role-based access
**Appetite:** 2 weeks
**Target maturity:** beta → ga
**Specs:** user-management
**Features:**
- User registration/login with password hashing
- JWT access/refresh tokens
- Role-based access (Admin, Operator, Viewer)
- Per-user API keys with role-scoped permissions
- Admin user management UI
- Password reset via email
**Success criteria:**
- [ ] Users can register and log in securely
- [ ] Roles correctly restrict access
- [ ] Per-user API keys inherit role permissions
- [ ] First registered user gets Admin role

### Maturity Promotion Path

| From | To | Gate Milestone | Requirements |
|------|-----|----------------|-------------|
| poc | alpha | M1 | CI/CD pipeline, 80% coverage, PRD exists, webhook MVP |
| alpha | beta | M3 | Structured logging, error handling, security hardening, all specs written |
| beta | ga | M8 + M9 | 30+ days stability, comprehensive monitoring, multi-user, sync management |

## 7. Key Features

### Feature 1: Log Collection API
REST endpoint (`POST /api/v1/sync-logs`) that receives raw rsync output with source name and timestamps. Authenticated via API key header. Automatically parses transfer statistics and stores structured data.

### Feature 2: Rsync Output Parser
Regex-based parser that extracts: total size, bytes sent/received, transfer speed, speedup ratio, file list, file count, and dry run detection from raw rsync output.

### Feature 3: Web Dashboard
Interactive Jinja2 + HTMX dashboard with sortable/filterable table of sync logs, detail modals, and Chart.js visualizations showing sync trends over time.

### Feature 4: Webhook Notifications (MVP)
Configurable webhook system that detects failed or anomalous syncs and sends alerts to Home Assistant and Discord endpoints.

## 8. Non-Functional Requirements

- **Performance:** Dashboard loads in < 2s for 1000+ log entries with pagination
- **Security:** API key authentication, no credential exposure, input validation on all endpoints
- **Reliability:** No data loss on log submission; graceful handling of malformed rsync output
- **Deployment:** Single `docker-compose up` for full stack deployment

## 9. Open Questions

- What constitutes a "failed" sync for notification purposes? (non-zero exit code, missing files, zero bytes transferred?)
- Should webhook configuration be stored in the database or environment variables?
- Is there a need for notification rate limiting / deduplication?

## 10. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-19 | 0.1.0 | finish06 | Initial draft from /add:init interview |
| 2026-02-22 | 0.2.0 | finish06 | Full roadmap with M3-M8 milestones, specs for all features, TODO conversion |
