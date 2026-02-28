# Rsync Log Viewer

A web application for collecting, parsing, and visualizing rsync synchronization logs. Built with FastAPI, PostgreSQL, and HTMX for homelab deployment.

[![CI](https://github.com/finish06/rsync-viewer/actions/workflows/ci.yml/badge.svg)](https://github.com/finish06/rsync-viewer/actions/workflows/ci.yml)

## Features

- **Log Collection** — REST API endpoint to receive rsync output with API key authentication
- **Automatic Parsing** — Extracts transfer stats, file counts, speeds, and file lists from raw rsync output
- **Web Dashboard** — Interactive table with filtering by source, date range, and sync type
- **Visualizations** — Charts showing sync duration, file counts, and bytes transferred over time
- **Failure Detection** — Exit code tracking and stale sync monitoring
- **Webhook Notifications** — Alerts via Discord or generic webhooks with retry logic and auto-disable
- **Notification History** — Dashboard tab with filters and pagination for past alerts
- **Dark Mode** — Light, dark, and system theme toggle
- **Multi-User Authentication** — User registration/login, JWT sessions, Admin/Operator/Viewer roles
- **OIDC Single Sign-On** — OpenID Connect authentication via PocketId, Authelia, Keycloak, or any OIDC provider
- **Per-User API Keys** — Role-scoped API keys with admin management UI
- **SMTP Email** — Admin-configurable SMTP settings with encrypted credentials
- **Reverse Proxy Support** — Works behind Nginx, Traefik, Caddy with correct URL resolution
- **Security Hardening** — Rate limiting, bcrypt API key hashing, CSRF protection, security headers
- **Structured Logging** — JSON log output with request tracing and sensitive data masking
- **Prometheus Metrics** — `/metrics` endpoint for monitoring with Grafana dashboard templates

## Architecture

See [docs/architecture.mmd](docs/architecture.mmd) for a full Mermaid diagram of the application architecture.

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 16+ (or use the provided Docker setup)

## Quick Start

### Using Docker Compose

```bash
cp .env.example .env
# Edit .env with your settings (API key, secret key, etc.)
docker-compose up -d
```

The application will be available at http://localhost:8000

### Getting Started

Once the application is running:

1. **Register the first user** — Navigate to http://localhost:8000/register and create an account. The first registered user is automatically granted the **Admin** role.
2. **Log in** — Go to http://localhost:8000/login with the credentials you just created.
3. **Generate an API key** — Navigate to Settings > API Keys and click "Generate Key". Use this key in the `X-API-Key` header when submitting sync logs via the API.
4. **Submit your first sync log** — Use the curl example in [API Usage](#api-usage) below with your new API key.

> **Note:** There is no default username or password. Authentication is disabled until the first user registers, at which point it activates automatically.

### Local Development

```bash
# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL (via Docker)
docker-compose up -d db

# Run the application
uvicorn app.main:app --reload
```

## Configuration

Environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://postgres:postgres@localhost:5432/rsync_viewer` |
| `APP_NAME` | Application name | `Rsync Log Viewer` |
| `DEBUG` | Enable debug mode | `true` |
| `SECRET_KEY` | Secret key for sessions | `change-me` |
| `DEFAULT_API_KEY` | API key for log submission | — |
| `RATE_LIMIT_AUTHENTICATED` | Rate limit for authenticated requests | `60/minute` |
| `RATE_LIMIT_UNAUTHENTICATED` | Rate limit for unauthenticated requests | `20/minute` |
| `MAX_REQUEST_BODY_SIZE` | Max request body in bytes | `10485760` (10 MB) |
| `REGISTRATION_ENABLED` | Allow new user registration | `true` |
| `ENCRYPTION_KEY` | Fernet key for encrypting OIDC/SMTP secrets | — |
| `FORCE_LOCAL_LOGIN` | Always show local login form (OIDC safety fallback) | `false` |
| `HSTS_ENABLED` | Enable Strict-Transport-Security header | `false` |
| `CSP_REPORT_ONLY` | Use CSP in report-only mode | `true` |

## Authentication

### Local Authentication

By default, the application uses local username/password authentication with JWT tokens. The first registered user is automatically granted the **Admin** role; subsequent users get the **Viewer** role.

### Disabling Registration

After creating your initial users, you can disable new user registration:

```env
REGISTRATION_ENABLED=false
```

When disabled, the `/register` page shows a "Registration is currently disabled" message and the API rejects registration attempts with a 403 error. Admins can still create users directly in the database if needed.

### OIDC Single Sign-On

OIDC authentication allows users to log in via an external identity provider (e.g., PocketId, Authelia, Keycloak) alongside or instead of local credentials.

- **Authorization Code Flow** with state and nonce validation
- **Auto-discovery** via `/.well-known/openid-configuration`
- **Auto-provisioning** — new OIDC users get a local account with Viewer role
- **Email linking** — existing local users are linked by matching email
- **OIDC-only mode** — option to hide the local login form
- **Admin Settings UI** — configure the OIDC provider (issuer URL, client ID/secret, provider name, scopes) from the web interface with Fernet-encrypted secret storage
- **Callback URL** — displayed in the Settings UI for easy provider configuration

| Variable | Description |
|----------|-------------|
| `FORCE_LOCAL_LOGIN` | Always show the local login form, even when OIDC is in "hide local login" mode |
| `ENCRYPTION_KEY` | Fernet key for encrypting OIDC client secret and SMTP credentials |

All OIDC provider settings are configured via the admin Settings UI, not environment variables.

## API Usage

### Submit a Sync Log

```bash
curl -X POST http://localhost:8000/api/v1/sync-logs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "source_name": "backup-server",
    "start_time": "2024-01-15T10:00:00Z",
    "end_time": "2024-01-15T10:05:00Z",
    "raw_content": "sending incremental file list\nfile1.txt\nsent 1.23K bytes received 45 bytes 850.00 bytes/sec\ntotal size is 5.67M speedup is 4,444.88"
  }'
```

### List Sync Logs

```bash
curl http://localhost:8000/api/v1/sync-logs
curl http://localhost:8000/api/v1/sync-logs?source_name=backup-server
```

### Manage Monitors

```bash
# Create a monitor for stale sync detection
curl -X POST http://localhost:8000/api/v1/monitors \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"source_name": "backup-server", "expected_interval_hours": 24}'
```

### Manage Webhooks

```bash
# Create a Discord webhook
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"name": "Discord Alerts", "url": "https://discord.com/api/webhooks/...", "webhook_type": "discord"}'
```

Full API documentation is available at http://localhost:8000/docs (Swagger UI).

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app

# Run in Docker (matches CI)
docker compose -f docker-compose.dev.yml run --rm test \
  pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=80
```

## CI/CD

The GitHub Actions pipeline runs on every push and PR to `main`:

1. **Lint** — `ruff check` and `ruff format --check`
2. **Type Check** — `mypy app/`
3. **Tests** — `pytest` with 80% coverage threshold
4. **Build & Push** — Docker image pushed to registry with `beta` tag (on merge to main only)

## Project Structure

```
rsync-viewer/
├── app/
│   ├── api/endpoints/        # REST API route handlers
│   ├── models/               # SQLModel database models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── services/             # Business logic (parser, webhooks, stale checker)
│   ├── static/               # CSS assets
│   ├── templates/            # Jinja2 HTML templates
│   ├── config.py             # Application settings
│   ├── csrf.py               # CSRF token generation/validation
│   ├── database.py           # Database connection
│   ├── errors.py             # Error codes and response helpers
│   ├── logging_config.py     # Structured JSON logging
│   ├── middleware.py          # Security headers, body size, CSRF middleware
│   └── main.py               # FastAPI application entry point
├── tests/                    # Test suite (596+ tests, 83% coverage)
├── specs/                    # Feature specifications
├── docs/                     # Documentation, milestones, plans
├── .github/workflows/        # CI/CD pipeline
├── docker-compose.yml        # Production Docker config
├── docker-compose.dev.yml    # Test Docker config
└── requirements.txt          # Python dependencies
```

## Contributing

Contributions are welcome! This project uses conventional commits (`feat:`, `fix:`, `docs:`, etc.) and requires PR review before merging to main.

## License

MIT
