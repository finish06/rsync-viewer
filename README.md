# Rsync Log Viewer

A web application for collecting, parsing, and visualizing rsync synchronization logs. Built with FastAPI, PostgreSQL, and HTMX.

## Overview

![Project Infographic](docs/infographic.svg)

## Features

- **Log Collection**: REST API endpoint to receive rsync output logs
- **Automatic Parsing**: Extracts transfer stats, file counts, speeds, and file lists from raw rsync output
- **Web Dashboard**: Interactive table with filtering by source, date range, and sync type
- **Visualizations**: Charts showing sync duration, file counts, and bytes transferred over time
- **Dry Run Detection**: Automatically identifies and filters dry run syncs

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- PostgreSQL 16+ (or use the provided Docker setup)

## Quick Start

### Using Docker Compose

```bash
cp .env.example .env
docker-compose up -d
```

The application will be available at http://localhost:8000

### Local Development

```bash
# Create virtual environment
python -m venv .venv
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
| `SECRET_KEY` | Secret key for sessions | - |
| `DEFAULT_API_KEY` | API key for log submission | - |

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

### Get Sync Log Details

```bash
curl http://localhost:8000/api/v1/sync-logs/{sync_id}
```

## Testing

```bash
pytest
```

With coverage:

```bash
pytest --cov=app
```

## Project Structure

```
rsync-viewer/
├── app/
│   ├── api/
│   │   └── endpoints/      # API route handlers
│   ├── models/             # SQLModel database models
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/           # Business logic (rsync parser)
│   ├── static/             # CSS assets
│   ├── templates/          # Jinja2 HTML templates
│   ├── config.py           # Application settings
│   ├── database.py         # Database connection
│   └── main.py             # FastAPI application
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── docker-compose.yml      # Docker configuration
└── requirements.txt        # Python dependencies
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
