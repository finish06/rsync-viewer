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
│   ├── api/endpoints/              # REST API route handlers
│   ├── models/                     # SQLModel database models
│   ├── schemas/                    # Pydantic request/response schemas
│   ├── services/                   # Business logic (rsync parser)
│   ├── static/                     # CSS assets
│   ├── templates/                  # Jinja2 HTML templates
│   ├── config.py                   # Application settings
│   ├── database.py                 # Database connection
│   └── main.py                     # FastAPI application entry point
├── tests/                          # Test suite
├── specs/                          # Feature specifications
├── docs/                           # Documentation (PRD, plans)
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
- **CI/CD:** GitHub Actions (to be scaffolded)

## Collaboration

- **Autonomy level:** Autonomous
- **Review gates:** PR review before merge to main
- **Deploy approval:** Required for production
