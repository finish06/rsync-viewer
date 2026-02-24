# Environment Variables

All configuration is managed through environment variables. Copy `.env.example` to `.env` and customize as needed.

## Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | — | Yes |
| `APP_NAME` | Application display name | `Rsync Log Viewer` | No |
| `DEBUG` | Enable debug mode | `false` | No |
| `SECRET_KEY` | Secret key for CSRF token signing | `change-me` | Yes (production) |
| `DEFAULT_API_KEY` | Default API key for development | `rsv_dev_key` | No |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` | No |
| `LOG_FORMAT` | Log output format (`json` or `text`) | `json` | No |
| `RATE_LIMIT_AUTHENTICATED` | Rate limit for authenticated requests | `60/minute` | No |
| `RATE_LIMIT_UNAUTHENTICATED` | Rate limit for unauthenticated requests | `20/minute` | No |
| `MAX_REQUEST_BODY_SIZE` | Maximum request body size in bytes | `10485760` (10 MB) | No |
| `HSTS_ENABLED` | Enable Strict-Transport-Security header | `false` | No |
| `CSP_REPORT_ONLY` | Use Content-Security-Policy-Report-Only | `true` | No |
| `DB_POOL_SIZE` | Database connection pool size | `10` | No |
| `DB_MAX_OVERFLOW` | Maximum overflow connections beyond pool size | `20` | No |
| `DB_POOL_TIMEOUT` | Seconds to wait for a pool connection | `30` | No |
| `QUERY_TIMEOUT_SECONDS` | Maximum query execution time in seconds | `30` | No |
| `METRICS_ENABLED` | Enable Prometheus `/metrics` endpoint | `true` | No |
| `DATA_RETENTION_DAYS` | Auto-delete sync logs older than N days (0 = disabled) | `0` | No |
| `RETENTION_CLEANUP_INTERVAL_HOURS` | Hours between retention cleanup runs | `24` | No |

## Database

```bash
# PostgreSQL connection string (psycopg driver)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rsync_viewer
```

When using Docker Compose, the default URL connects to the `db` service automatically.

## Security

```bash
# Generate a strong secret key for production
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Generate a secure API key
DEFAULT_API_KEY=$(python -c "import secrets; print('rsv_' + secrets.token_urlsafe(24))")
```

- `SECRET_KEY` is used for CSRF token signing. Change it from the default in production.
- `DEFAULT_API_KEY` is created on first startup. Generate a unique key for production use.
- `HSTS_ENABLED` should only be enabled when serving behind HTTPS.

## Rate Limiting

Rate limits use the format `{count}/{period}` where period is `second`, `minute`, `hour`, or `day`.

```bash
RATE_LIMIT_AUTHENTICATED=60/minute
RATE_LIMIT_UNAUTHENTICATED=20/minute
```

## Metrics & Retention

```bash
# Enable Prometheus metrics at /metrics
METRICS_ENABLED=true

# Auto-delete logs older than 90 days (0 = keep forever)
DATA_RETENTION_DAYS=90

# Run cleanup every 24 hours
RETENTION_CLEANUP_INTERVAL_HOURS=24
```

When `DATA_RETENTION_DAYS` is set to `0` (the default), no automatic cleanup occurs and all logs are retained indefinitely.
