# Architecture

## System Overview

Rsync Log Viewer is a web application for collecting, parsing, and visualizing rsync synchronization logs. It is designed for homelab and self-hosted deployment using Docker Compose.

```mermaid
graph TD
    subgraph Client
        RS[rsync script / cron]
        BR[Browser]
        PR[Prometheus]
    end

    subgraph Application
        API[FastAPI REST API]
        HTMX[HTMX UI Layer]
        MW[Middleware Stack]
        PS[Parser Service]
        NS[Notification Service]
        RS_SVC[Retention Service]
        MET[Metrics Collector]
    end

    subgraph Storage
        PG[(PostgreSQL 16)]
    end

    subgraph External
        WH[Webhook Endpoints<br/>Discord / Generic]
    end

    RS -->|POST /api/v1/sync-logs| API
    BR -->|HTTP / HTMX| HTMX
    PR -->|GET /metrics| MET
    API --> MW
    HTMX --> MW
    MW --> PS
    MW --> NS
    API --> PG
    HTMX --> PG
    NS -->|HTTP POST| WH
    RS_SVC -->|cleanup old logs| PG
    MET -->|expose counters| API
```

## Key Components

### FastAPI Application (`app/main.py`)

The main application entry point. Registers middleware, routers, exception handlers, and the HTMX template engine. Serves both the REST API and the web dashboard.

### Middleware Stack (`app/middleware.py`, `app/metrics.py`)

Middleware runs in this order (outermost first):

1. **SecurityHeadersMiddleware** — Adds X-Content-Type-Options, X-Frame-Options, CSP, HSTS headers
2. **BodySizeLimitMiddleware** — Rejects requests exceeding `MAX_REQUEST_BODY_SIZE`
3. **PrometheusMiddleware** — Tracks API request counts and durations
4. **SlowAPIMiddleware** — Enforces rate limiting per API key or IP
5. **CsrfMiddleware** — Validates CSRF double-submit cookie tokens on HTMX form submissions
6. **AuthRedirectMiddleware** — Redirects unauthenticated browser requests to `/login` (skips API routes + public paths)
7. **RequestLoggingMiddleware** — Structured JSON logging with request IDs and correlation

### REST API (`app/api/endpoints/`)

- **sync_logs** — CRUD for rsync log ingestion and querying (cursor + offset pagination)
- **monitors** — Sync source monitoring (staleness detection)
- **failures** — Failure event tracking and queries
- **webhooks** — Webhook endpoint management
- **analytics** — Aggregated statistics, trends, and CSV/JSON export
- **auth** — JWT authentication (register, login, refresh, password reset)
- **api_keys** — Per-user API key management (create, list, revoke)
- **users** — Admin user management (list, role change, enable/disable, delete)

### HTMX UI Routes (`app/routes/`)

- **pages** — Page-level routes (`/`, `/login`, `/register`, `/settings`, `/admin/users`)
- **auth** — Login/logout form handlers + OIDC SSO flow
- **dashboard** — HTMX partials for sync table, charts, analytics, notifications, changelog
- **settings** — SMTP, OIDC, and synthetic monitoring configuration forms
- **api_keys** — HTMX API key CRUD
- **webhooks** — HTMX webhook CRUD with toggle and test
- **admin** — User management table with role/status controls

### Auth & RBAC (`app/api/deps.py`)

Dual authentication: API keys (X-API-Key header) and JWT (Bearer header or httpOnly cookie). Three roles: `viewer` < `operator` < `admin`. Per-user API keys support role overrides. Legacy keys (no user_id) default to operator.

### Parser Service (`app/services/rsync_parser.py`)

Parses raw rsync output to extract structured data: bytes transferred, file counts, transfer speed, speedup ratio, file lists, and dry-run detection.

### Webhook Dispatcher (`app/services/webhook_dispatcher.py`)

Sends webhook notifications when failure events occur. Supports generic JSON webhooks and Discord-formatted embeds with retry logic (30s → 60s → 120s backoff, max 3 attempts). Auto-disables endpoints after 10 consecutive failures.

### Synthetic Monitoring (`app/services/synthetic_check.py`)

Background self-test loop: periodically POSTs a canned rsync log to the app's own API, verifies the response, DELETEs the created log, and fires webhooks on failure. DB-backed config with runtime start/stop via settings UI.

### Stale Source Checker (`app/services/stale_checker.py`)

Evaluates enabled monitors to detect sources that haven't synced within their expected interval (plus grace multiplier). Creates FailureEvents for stale sources.

### Auth Service (`app/services/auth.py`)

JWT token management: access token creation/validation, refresh token rotation, bcrypt password hashing, and RBAC role hierarchy.

### Retention Service (`app/services/retention.py`)

Background task that periodically cleans up sync logs older than `DATA_RETENTION_DAYS`. Deletes in FK cascade order: notification_logs → failure_events → sync_logs.

### Metrics Collector (`app/metrics.py`)

Prometheus metrics using a custom `CollectorRegistry`:
- **Sync metrics:** totals, duration histogram, files/bytes counters (per source)
- **API metrics:** request totals and duration histogram (per endpoint/method)
- **Health metrics:** application version info gauge

### Database (`app/database.py`)

SQLModel ORM with PostgreSQL 16. Connection pooling configured via `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, and `DB_POOL_TIMEOUT`.

### Frontend (`app/templates/`)

Server-side rendered HTML using Jinja2 templates with HTMX for dynamic updates. No JavaScript build step required.

## Data Flow

### Sync Log Submission

1. An rsync script or cron job sends a POST request to `/api/v1/sync-logs` with the raw rsync output
2. The API validates the request and authenticates via the `X-API-Key` header
3. The rsync parser extracts structured fields from the raw content
4. The parsed sync log is stored in PostgreSQL
5. Prometheus sync metrics are updated (totals, duration, files, bytes)
6. If the sync failed (non-zero exit code), a failure event is created
7. Active webhook endpoints matching the source are notified

### Dashboard Viewing

1. The browser requests the main page (`/`)
2. FastAPI renders the Jinja2 template with HTMX attributes
3. HTMX fetches table data, charts, and analytics via partial endpoints (`/htmx/*`)
4. Filters and pagination update dynamically without full page reloads

### Metrics Scraping

1. Prometheus scrapes `GET /metrics` at a configured interval
2. The endpoint returns all counters, histograms, and gauges in Prometheus exposition format
3. Grafana dashboards visualize the scraped metrics

## Deployment

The application is containerized with Docker Compose:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `app` | Local build | 8000 | FastAPI application |
| `db` | postgres:16-alpine | 5432 | PostgreSQL database |

Database state is persisted in a Docker volume (`postgres_data`). See [Setup Guide](setup.md) for deployment instructions.
