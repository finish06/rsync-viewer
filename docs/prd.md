# Rsync Log Viewer — Product Requirements Document

**Version:** 0.4.0
**Created:** 2026-02-19
**Author:** finish06
**Status:** Active

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

- ~~OIDC single sign-on authentication (M7)~~ — COMPLETE
- ~~Multi-user authentication and role-based access (M9)~~ — COMPLETE
- ~~Prometheus metrics export and Grafana dashboards (M6)~~ — COMPLETE
- Source health dashboard with sparklines (M12)
- Live SSE dashboard updates (M13)
- Internal event bus for decoupled integrations (M14)
- Home Assistant + Grafana ecosystem integrations (M15)
- `rsv` CLI tool for zero-friction rsync wrapping (M14)
- Rsync client container with auto log shipping (M15)

## 5. Architecture

### Tech Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Language (backend) | Python | 3.11+ | Primary application language |
| Backend Framework | FastAPI | latest | Async web framework with OpenAPI support |
| ORM | SQLModel | latest | SQLAlchemy + Pydantic integration |
| Database | PostgreSQL | 16+ | JSONB for file lists, indexed queries |
| Frontend (insight UI) | React 19 + TypeScript + Vite | latest | SPA under `frontend/`, built into `app/static/app/`, served by FastAPI (M16) |
| Frontend (admin/settings/auth) | Jinja2 + HTMX | latest | Server-rendered; low-frequency screens, migrated last |
| Charts / data | Recharts, TanStack Query, React Router | latest | Client-side charts and data fetching against `/api/v1` |
| Containerization | Docker + Docker Compose | latest | Multi-stage build (node → python); single container |

**Frontend architecture decision (2026-08-29, M16):** the dashboard is rebuilt as a React SPA because the insight-first UI (drill-down, cross-filtering, live status, client-side chart interaction) is impractical with server-rendered partials. The SPA consumes the existing cookie-authenticated `/api/v1` JSON API and is shipped in the same container — no separate deploy, no CORS. Login, settings, and admin remain Jinja2/HTMX until the SPA is the default experience; they are visited occasionally and gain little from a rebuild.

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

### Current Maturity: GA (v2.5.0, promoted 2026-03-03)

### Roadmap

#### Completed (v1.0–v2.5)

| Milestone | Goal | Status |
|-----------|------|--------|
| M1: Foundation | CI/CD, 80% coverage, conventional commits | COMPLETE |
| M2: Notifications | Webhook alerts, Discord, settings UI | COMPLETE |
| M3: Reliability | Structured logging, security hardening | COMPLETE |
| M4: Analytics & Performance | Statistics API, charts, cursor pagination | COMPLETE |
| M5: API Performance | API key debounce | COMPLETE |
| M6: Observability | Prometheus metrics, Grafana dashboards, docs | COMPLETE |
| M9: Multi-User | JWT auth, RBAC, per-user API keys | COMPLETE |
| M11: Polish & Infrastructure | SMTP email, responsive UI, cleanup | COMPLETE |
| M7: OIDC Authentication | OpenID Connect SSO | COMPLETE |
| M-GA: GA Promotion | Smoke tests, PR template, glossary, SLAs | COMPLETE |

#### Next: 2026 Roadmap (Q2–Q3)

*Source: 3-agent swarm analysis (2026-03-20) — `.swarm/roadmap/final.md`*

| Milestone | Theme | Duration | Status |
|-----------|-------|----------|--------|
| M16: Insight UI | Rebuild the dashboard as an interactive React SPA: condensed overview with drill-down, transfers over time, new shows/movies, prominent uptime | 4 weeks | DONE (v2.7.0–v2.12.0, 2026-08-29) |
| M17: Settings in the SPA | Move API keys, webhooks, email, sign-in, monitoring, users, and changelog into `/app/settings`; retire the HTMX settings pages | 2 weeks | NOW |
| M12: See Everything | Remaining items not absorbed by M16 (monitor management UI, onboarding wizard) | 2 weeks | NEXT |
| M13: Stay & Trust | Live dashboard, smart notifications, backup/restore | 3 weeks | NEXT |
| M14: Build to Last | Event bus, `rsv` CLI, async DB, API versioning | 4 weeks | LATER |
| M15: Grow the Ecosystem | Home Assistant, Grafana templates, PWA, client container | 3 weeks | LATER |

#### M16: "Insight UI" (DONE — added and shipped 2026-08-29; UX artifact awaiting formal sign-off)
**Goal:** Replace the click-to-see-information dashboard with a UI that shows what happened at a glance and lets the user dive into detail: what was transferred (condensed, expandable), how transfers trend over time, which new shows and movies arrived, and — most prominently — whether the system is up and syncing (synthetic monitoring, source liveness). Settings become a secondary destination.
**Appetite:** 4 weeks
**Target maturity:** ga (no regression in gates; SPA gets its own unit tests + existing Playwright E2E)
**Spec:** specs/insight-ui.md · **UX:** specs/ux/insight-ui-ux.md
**Deliverables:**

| Deliverable | Effort | Notes |
|------------|--------|-------|
| SPA scaffold + build pipeline | 2d | `frontend/` (Vite, React, TS), served at `/app`, multi-stage Dockerfile, CI job (lint, typecheck, vitest) |
| Overview page: liveness banner + source health cards + activity strip | 5d | Synthetic uptime %, last check, streak; per-source status/last sync/sparkline; condensed "what was sent" feed |
| Transfers page: condensed timeline with drill-down | 4d | Grouped by day/source, expand to files, failure details inline |
| Trends page: transfers over time | 3d | Bytes/files/duration/success over time with cross-filtering, source comparison |
| Media page: new shows & movies | 4d | Backend media classifier over `file_list` (TV vs movie path heuristics) + API + UI |
| Uptime page: synthetic monitoring history | 2d | Check history API + heatmap/timeline; also feeds the overview banner |
| Cut-over: `/` serves the SPA; legacy tabs removed | 1d | Settings/admin/login links preserved |

**Success criteria:**
- [x] "Is everything OK?" answerable from the overview in under 2 seconds without a click (TC-001, `tests/screenshots/insight-ui/step-01-overview.png`)
- [x] Any transfer's files and failure details reachable in ≤ 2 clicks from the overview (TC-002)
- [x] New shows/movies from the last 7 days listed by title, not by file path (TC-005)
- [x] Synthetic uptime (%) and last-check age visible on every page header (AC-001, liveness pill)
- [x] Existing Playwright E2E suite green against the SPA; SPA unit coverage ≥ 80% (unit coverage 88 %; dashboard/analytics/login E2E rewritten in C6 and green locally)

#### M12: "See Everything" (Weeks 1–3)
Unlock existing backend capabilities + nail the first impression.

| Deliverable | Effort | Notes |
|------------|--------|-------|
| Sync Monitor Management UI | 2–3d | Create/edit/delete monitors from dashboard (backend exists, no UI) |
| Failure Drill-Down View | 1–2d | Stderr, exit code, file list — one click from sync table |
| Source Health Dashboard + Sparklines | 5–7d | Status cards with at-a-glance health per source |
| Onboarding Wizard | 3–5d | Zero-state detection, pre-filled scripts, "waiting for first sync" |
| Relative Timestamps + Timezone | 1–2d | "3m ago" within 24h window |
| Webhook Test Button + OpenAPI Docs Link | 1d | Quick wins — wire existing backend features |

**Success criteria:** New user goes from `docker-compose up` to first monitored sync in < 5 minutes. Source health visible at a glance. Failed sync details one click away.

#### M13: "Stay & Trust" (Weeks 4–6)
Make the daily experience delightful + build operational trust.

| Deliverable | Effort | Notes |
|------------|--------|-------|
| Live Dashboard (SSE) | 5–7d | Auto-refresh within 2s of new sync arrival |
| Smart Notifications | 3–5d | Context, deep links, streak info, comparison to baseline |
| Backup & Restore Tooling | 2–3d | pg_dump scripts, rotation, documented recovery |
| Global Search (PostgreSQL FTS) | 2–3d | Full-text search across sources, hostnames, errors |
| CSV/JSON Analytics Export | 1d | One-click export |
| Keyboard Shortcuts | 1–2d | j/k navigation, /, Enter, Escape |
| Mobile-Responsive Polish | 1–2d | No horizontal scroll, correct tap targets |

**Success criteria:** Dashboard updates live. Discord notifications include direct links + "3rd consecutive failure" context. Backup + restore tested and documented.

#### M14: "Build to Last" (Weeks 7–10)
Architectural hardening + developer platform.

| Deliverable | Effort | Notes |
|------------|--------|-------|
| Internal Event Bus | 2w | `sync_log.created`, `sync_log.failed`, `monitor.stale_detected` events |
| `rsv` CLI Tool | 5–7d | `rsv push`, `rsv wrap -- rsync ...` captures output + timing |
| API Versioning Policy | 1w | Deprecation headers, documented sunset schedule |
| DB Migration Automation | 1w | alembic check in CI, rollback testing |
| Improved Detail Modal | 3–5d | Syntax highlighting, diff view, file grouping |
| Async Database Layer | 2–3w | AsyncSession + asyncpg, non-blocking p95 |

**Success criteria:** All side-effects fire via event bus. `rsv wrap` captures output automatically. All DB operations non-blocking.

#### M15: "Grow the Ecosystem" (Weeks 11–14)
Connect to the broader homelab stack.

| Deliverable | Effort | Notes |
|------------|--------|-------|
| Rsync Client Container | 5–7d | Alpine image, auto-ships logs to viewer |
| Home Assistant Integration | 3–4d | Sensors for sync status, failure count |
| Grafana Dashboard Templates | 2d | Pre-built dashboards consuming Prometheus metrics |
| PWA Support | 3–5d | Installable, offline last-known status, app icon |
| Webhook Template Library | 2d | Discord, Slack, Telegram, Pushover presets |

**Success criteria:** Official client container auto-reports. Home Assistant sensors show sync health. App installable on phone home screen.

#### Deferred (Revisit on Demand)

| Item | Reason | Revisit When |
|------|--------|--------------|
| Multi-Tenant Architecture | RBAC covers household use; disproportionate effort | Demand from multi-user deployments |
| Horizontal Scaling (Redis) | Single-server homelab doesn't benefit | >10 concurrent connections sustained |
| Plugin/Extension Architecture | Speculative; each backup tool differs | Community requests for Borgmatic/Restic support |
| Source Grouping / Tags | Premature for 5–20 sources | Users with 50+ sources |
| Bulk Log Import | Onboarding wizard solves cold-start differently | Explicit user requests |

### Dependency Chain

**Completed milestones:**
```
M1 → M2 → M3 → M4 → M6 → M9 → M11 → M7 → M-GA (all COMPLETE)
```

**2026 roadmap:**
```
M12 (See Everything) → M13 (Stay & Trust) → M14 (Build to Last) → M15 (Ecosystem)
```

M12 has zero backend dependencies (pure UI wiring). M13's SSE builds on M12's source health dashboard. M14's event bus benefits from M13's notification improvements. M15's client container benefits from M14's `rsv` CLI and event bus.

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

#### M4: Analytics & Performance [COMPLETE]
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

#### M6: Observability [COMPLETE]
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
- [x] /metrics returns valid Prometheus format
- [x] Grafana dashboards visualize sync and API metrics
- [x] New developers can deploy using only documentation
- [x] All environment variables documented

#### M7: OIDC Authentication [COMPLETE]
**Goal:** Add OpenID Connect SSO as optional auth method
**Appetite:** 1 week
**Target maturity:** beta → ga
**Specs:** oidc-authentication, oidc-settings
**Completed:** 2026-02-27 (PR #20)
**Features:**
- OIDC Authorization Code Flow with state/nonce validation
- OIDC Discovery (`.well-known/openid-configuration`)
- Auto-create/link local accounts from OIDC claims
- Provider-branded login button, optional OIDC-only mode
- Admin OIDC settings UI with Fernet-encrypted client secret
- Performance optimizations (API key prefix filter, async SMTP, changelog caching)
**Success criteria:**
- [x] OIDC login works with PocketId and generic providers
- [x] New users auto-created with Viewer role
- [x] Existing users auto-linked by email
- [x] Local JWT session issued after OIDC login

#### M10: Rsync Client & Sync Management [LATER]
**Goal:** Provide decentralized rsync client containers that run at the edge and ship logs to the central Rsync Viewer hub
**Appetite:** 1 week
**Target maturity:** beta → ga
**Specs:** rsync-client-compose
**Features:**
- Custom Alpine Docker image (<30MB) with rsync + cron + curl
- Pull mode (remote→local) and push mode (local→remote) compose examples
- Cron-scheduled rsync with automatic log submission to viewer API
- SSH key mounting, configurable rsync args, custom SSH port
- Graceful handling of API downtime (no crash, retry next cycle)
- README with setup, configuration, and troubleshooting
**Success criteria:**
- [ ] Alpine client image builds and is <30MB
- [ ] Pull and push compose examples work end-to-end
- [ ] Logs appear in the Rsync Viewer dashboard automatically
- [ ] Graceful API failure handling (no crash, retry next cycle)
- [ ] README covers all usage scenarios

#### M9: Multi-User [COMPLETE]
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
- [x] Users can register and log in securely
- [x] Roles correctly restrict access
- [x] Per-user API keys inherit role permissions
- [x] First registered user gets Admin role

### Maturity Promotion Path

| From | To | Gate Milestone | Requirements | Status |
|------|-----|----------------|-------------|--------|
| poc | alpha | M1 | CI/CD pipeline, 80% coverage, PRD exists | DONE (2026-02-20) |
| alpha | beta | M3 | Structured logging, error handling, security hardening | DONE (2026-02-24) |
| beta | ga | M-GA | 30+ days stability, monitoring, multi-user, SLAs | DONE (2026-03-03) |

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

## 9. Service Level Targets

Homelab best-effort targets. Not contractual SLAs — these are monitoring thresholds to detect degradation.

| Metric | Target | Measurement |
|--------|--------|-------------|
| Availability | 99% uptime | Synthetic check + /health endpoint |
| API response (P95) | < 500ms | Prometheus histogram |
| API response (P99) | < 2000ms | Prometheus histogram |
| Ingestion success rate | 99.9% | sync_logs_total success vs error |
| Webhook delivery latency | < 60s | Time from failure detection to webhook POST |

## 10. Scalability

Rsync Log Viewer is designed for single-instance homelab deployment:

- **Target load:** 10-50 sync sources, ~1000 logs/day
- **Database:** Single PostgreSQL instance with configurable data retention
- **Horizontal scaling:** Not required; single Docker Compose stack
- **Storage:** Log growth bounded by `DATA_RETENTION_DAYS` auto-cleanup

## 11. Open Questions

- What constitutes a "failed" sync for notification purposes? (non-zero exit code, missing files, zero bytes transferred?)
- Should webhook configuration be stored in the database or environment variables?
- Is there a need for notification rate limiting / deduplication?

## 12. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-19 | 0.1.0 | finish06 | Initial draft from /add:init interview |
| 2026-02-22 | 0.2.0 | finish06 | Full roadmap with M3-M10 milestones, specs for all features, TODO conversion |
| 2026-03-20 | 0.3.0 | finish06 | 2026 roadmap (M12-M15) from 3-agent swarm analysis; all prior milestones marked COMPLETE |
| 2026-08-29 | 0.4.0 | finish06 | M16 Insight UI: React SPA rebuild of the dashboard (frontend architecture decision), M12 rescoped |
