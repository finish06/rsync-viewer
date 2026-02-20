# Rsync Log Viewer — Product Requirements Document

**Version:** 0.1.0
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

### Out of Scope

- Multi-user authentication and role-based access
- Scheduled rsync execution (this tool monitors, not triggers)
- Prometheus metrics export (future enhancement)
- Mobile-native app
- Cloud-hosted SaaS deployment

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

### Current Maturity: POC

### Roadmap

| Milestone | Goal | Target Maturity | Status | Success Criteria |
|-----------|------|-----------------|--------|------------------|
| M1: Foundation | Stabilize existing features, add CI/CD | poc → alpha | NOW | CI pipeline, 80% coverage, conventional commits |
| M2: Notifications | Webhook alerts for failed syncs | alpha | NEXT | HA/Discord webhooks working, < 60s latency |
| M3: Reliability | Error handling, logging, security hardening | alpha → beta | LATER | Structured logging, input validation, rate limiting |
| M4: Analytics | Enhanced visualizations and metrics | beta | LATER | Per-source dashboards, trend analysis |

### Milestone Detail

#### M1: Foundation [NOW]
**Goal:** Establish CI/CD pipeline, improve test coverage, adopt conventional commits
**Appetite:** 1-2 weeks
**Target maturity:** alpha
**Features:**
- GitHub Actions CI pipeline (lint, test, coverage)
- Comprehensive error handling with consistent response format
- Structured logging with request/response tracking
- Test coverage to 80%+
**Success criteria:**
- [ ] GitHub Actions runs on every PR
- [ ] Test coverage >= 80%
- [ ] All existing tests pass in CI
- [ ] Conventional commit format adopted

#### M2: Notifications [NEXT]
**Goal:** Alert users when syncs fail via webhooks
**Appetite:** 1 week
**Target maturity:** alpha
**Features:**
- Webhook notification service (configurable endpoints)
- Home Assistant integration
- Discord webhook integration
- Failure detection logic
**Success criteria:**
- [ ] Failed sync triggers webhook within 60 seconds
- [ ] Home Assistant and Discord integrations tested
- [ ] Notification history viewable in dashboard

### Maturity Promotion Path

| From | To | Requirements |
|------|-----|-------------|
| poc | alpha | CI/CD pipeline, 80% coverage, PRD exists, webhook MVP |
| alpha | beta | Full specs for all features, TDD adopted, error handling complete |
| beta | ga | 30+ days stability, comprehensive monitoring, security hardened |

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
