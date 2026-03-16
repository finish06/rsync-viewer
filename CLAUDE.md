# Rsync Log Viewer

Web application for collecting, parsing, and visualizing rsync synchronization logs. Built with FastAPI, PostgreSQL, and HTMX for homelab deployment.

## Methodology

This project follows **Agent Driven Development (ADD)** — specs drive agents, humans architect and decide, trust-but-verify ensures quality.

- **PRD:** docs/prd.md
- **Specs:** specs/
- **Plans:** docs/plans/
- **Config:** .add/config.json

Document hierarchy: PRD → Spec → Plan → User Test Cases → Automated Tests → Implementation

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Python | 3.11+ |
| Framework | FastAPI | latest |
| ORM | SQLModel | latest |
| Database | PostgreSQL | 16+ |
| Frontend | Jinja2 + HTMX | latest |
| Containers | Docker Compose | latest |

## Commands

### Development
```
docker-compose up -d                # Start local dev (app + db)
uvicorn app.main:app --reload       # Run app locally (needs db)
pytest                              # Run all tests
pytest --cov=app                    # Run tests with coverage
ruff check .                        # Lint check
ruff format .                       # Auto-format
mypy app/                           # Type check
```

### ADD Workflow
```
/add:init                            # Initialize ADD (already done)
/add:spec {feature}                  # Create feature specification
/add:plan specs/{feature}.md         # Create implementation plan
/add:tdd-cycle specs/{feature}.md    # Execute TDD cycle
/add:verify                          # Run quality gates
/add:deploy                          # Commit and deploy
/add:away {duration}                 # Human stepping away
/add:back                            # Human returning
```

## Architecture

### Key Directories
```
rsync-viewer/
├── app/                            # Application source code
│   ├── api/
│   │   ├── endpoints/              # REST API route handlers
│   │   │   ├── sync_logs.py        # Log ingestion + querying (CRUD)
│   │   │   ├── monitors.py         # Sync source staleness monitors
│   │   │   ├── failures.py         # Failure event queries
│   │   │   ├── webhooks.py         # Webhook endpoint management
│   │   │   ├── analytics.py        # Aggregated stats + export
│   │   │   ├── auth.py             # JWT auth (register/login/refresh/reset)
│   │   │   ├── api_keys.py         # Per-user API key management
│   │   │   └── users.py            # Admin user management
│   │   └── deps.py                 # Auth dependencies (API key, JWT, RBAC)
│   ├── routes/                     # HTMX / UI route handlers
│   │   ├── pages.py                # Page-level routes (/, /login, /settings, etc.)
│   │   ├── auth.py                 # Login/logout/register/OIDC form handlers
│   │   ├── dashboard.py            # HTMX partials (sync table, charts, analytics)
│   │   ├── settings.py             # SMTP, OIDC, synthetic monitoring settings
│   │   ├── api_keys.py             # HTMX API key CRUD
│   │   ├── webhooks.py             # HTMX webhook CRUD
│   │   └── admin.py                # Admin user management UI
│   ├── models/                     # SQLModel database models
│   │   ├── sync_log.py             # SyncLog + ApiKey
│   │   ├── user.py                 # User + RefreshToken + PasswordResetToken
│   │   ├── monitor.py              # SyncSourceMonitor
│   │   ├── failure_event.py        # FailureEvent
│   │   ├── webhook.py              # WebhookEndpoint
│   │   ├── webhook_options.py      # WebhookOptions (Discord config)
│   │   ├── notification_log.py     # NotificationLog
│   │   ├── smtp_config.py          # SmtpConfig
│   │   ├── oidc_config.py          # OidcConfig
│   │   ├── synthetic_check_config.py   # SyntheticCheckConfig
│   │   └── synthetic_check_result.py   # SyntheticCheckResultRecord
│   ├── schemas/                    # Pydantic request/response schemas
│   ├── services/                   # Business logic
│   │   ├── rsync_parser.py         # Parse raw rsync output
│   │   ├── auth.py                 # JWT token creation/validation, RBAC
│   │   ├── webhook_dispatcher.py   # Webhook delivery with retry + auto-disable
│   │   ├── webhook_test.py         # Test webhook delivery
│   │   ├── stale_checker.py        # Monitor staleness detection
│   │   ├── retention.py            # Background data cleanup
│   │   ├── synthetic_check.py      # Self-test POST/DELETE loop
│   │   ├── email.py                # SMTP email sending
│   │   ├── oidc.py                 # OpenID Connect integration
│   │   ├── registration.py         # User registration logic
│   │   ├── sync_filters.py         # Query filter helpers
│   │   └── changelog_parser.py     # CHANGELOG.md parser
│   ├── static/                     # CSS assets
│   ├── templates/                  # Jinja2 HTML templates
│   ├── config.py                   # Application settings (env vars)
│   ├── database.py                 # Database connection + pooling
│   ├── middleware.py               # Auth redirect, CSRF, security headers, body size limit, logging
│   ├── logging_config.py           # Structured logging setup (JSON/text format)
│   ├── rate_limit.py              # Shared SlowAPI rate limiter instance
│   ├── metrics.py                  # Prometheus metrics collector
│   ├── csrf.py                     # CSRF token generation/validation
│   ├── errors.py                   # Structured error response helpers
│   ├── templating.py               # Jinja2 template engine + filters
│   ├── utils.py                    # Shared utilities (utc_now, etc.)
│   └── main.py                     # FastAPI application entry point
├── tests/                          # Test suite
├── specs/                          # Feature specifications
├── docs/                           # Documentation (PRD, plans, architecture)
├── .add/                           # ADD methodology state
├── scripts/                        # Utility scripts
├── docker-compose.yml              # Docker configuration
└── requirements.txt                # Python dependencies
```

### Environments

- **Local:** Docker Compose (`docker-compose up -d`) at http://localhost:8000
- **Production:** Self-hosted homelab, deployed on merge to main

## Quality Gates

- **Mode:** Standard
- **Coverage threshold:** 80%
- **Type checking:** Blocking (mypy)
- **E2E required:** No

All gates defined in `.add/config.json`. Run `/add:verify` to check.

## Source Control

- **Git host:** GitHub (finish06/rsync-viewer)
- **Branching:** Feature branches off `main`
- **Commits:** Conventional commits (feat:, fix:, test:, refactor:, docs:)
- **CI/CD:** GitHub Actions (`.github/workflows/ci.yml`, `smoke-test.yml`)

## Collaboration

- **Autonomy level:** Autonomous
- **Review gates:** PR review before merge to main
- **Deploy approval:** Required for production
