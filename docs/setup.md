# Development & Deployment Setup Guide

## Prerequisites

- **Docker** and **Docker Compose** (recommended for all environments)
- **Python 3.11+** (only needed for local development without Docker)
- **PostgreSQL 16+** (only needed if running without Docker)
- **Git** for cloning the repository

## Quick Start with Docker Compose

The fastest way to get running:

```bash
# Clone the repository
git clone https://github.com/finish06/rsync-viewer.git
cd rsync-viewer

# Copy the environment file
cp .env.example .env

# Start the application and database
docker-compose up -d

# Verify it's running
curl http://localhost:8000/health
# → {"status":"ok"}
```

The application will be available at **http://localhost:8000**.

## Local Development Setup

For development with hot-reloading:

### 1. Clone and set up Python environment

```bash
git clone https://github.com/finish06/rsync-viewer.git
cd rsync-viewer

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Start PostgreSQL

Either use Docker for just the database:

```bash
docker-compose up -d db
```

Or install PostgreSQL locally and create the database:

```bash
createdb rsync_viewer
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your database URL if not using Docker defaults
```

### 4. Run the application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Submit a test sync log

```bash
curl -X POST http://localhost:8000/api/v1/sync-logs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: rsv_dev_key" \
  -d '{
    "source_name": "test-backup",
    "start_time": "2026-01-01T00:00:00Z",
    "end_time": "2026-01-01T00:05:00Z",
    "raw_content": "sent 1,234 bytes  received 5,678 bytes  2,304.00 bytes/sec\ntotal size is 10,000  speedup is 1.45",
    "exit_code": 0
  }'
```

Visit **http://localhost:8000** to see the dashboard.

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/test_api.py -v

# Lint and type checking
ruff check .
ruff format --check .
mypy app/
```

## Docker Compose Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `app` | Local build | 8000 | FastAPI application |
| `db` | postgres:16-alpine | 5432 | PostgreSQL database |

Data is persisted in a Docker volume (`postgres_data`).

## Production Deployment

For homelab or self-hosted production:

1. Set strong values in `.env`:
   - `SECRET_KEY` — a random string for CSRF token signing
   - `DEFAULT_API_KEY` — a secure API key (or create keys via the API)
   - `DEBUG=false`
2. Run with Docker Compose: `docker-compose up -d`
3. Optionally set `DATA_RETENTION_DAYS` to auto-clean old logs
4. Optionally set up Prometheus scraping of `/metrics`

See [Environment Variables](environment-variables.md) for all configuration options.
