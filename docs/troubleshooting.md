# Troubleshooting

## Database Connection Issues

### Cannot connect to PostgreSQL

**Symptom:** Application fails to start with a database connection error.

**Causes and fixes:**

1. **Database not running:**
   ```bash
   docker-compose up -d db
   # Verify it's up
   docker-compose ps
   ```

2. **Wrong DATABASE_URL:**
   Check your `.env` file. The default Docker Compose URL is:
   ```
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rsync_viewer
   ```
   If running inside Docker, use the service name instead of `localhost`:
   ```
   DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/rsync_viewer
   ```

3. **Port conflict:**
   Another service may be using port 5432. Check with:
   ```bash
   lsof -i :5432
   ```

### Connection pool exhaustion

**Symptom:** Requests hang or timeout under load.

**Fix:** Increase pool settings in `.env`:
```bash
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

## Docker Issues

### Container fails to start

**Symptom:** `docker-compose up` exits immediately.

1. Check logs:
   ```bash
   docker-compose logs app
   docker-compose logs db
   ```

2. Ensure the `.env` file exists:
   ```bash
   cp .env.example .env
   ```

3. Rebuild the image if dependencies changed:
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Docker networking issues

**Symptom:** App container cannot reach the database container.

1. Verify both containers are on the same network:
   ```bash
   docker network ls
   docker network inspect rsync-viewer_default
   ```

2. Ensure the `DATABASE_URL` uses the Docker service name `db`, not `localhost`:
   ```
   DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/rsync_viewer
   ```

### Volume permissions

**Symptom:** Database data not persisting across restarts.

Verify the Docker volume exists:
```bash
docker volume ls | grep postgres_data
```

## API Issues

### 401 Unauthorized

**Symptom:** API returns `{"error": "API key required"}`.

**Fix:** Include the `X-API-Key` header in your request:
```bash
curl -H "X-API-Key: rsv_dev_key" http://localhost:8000/api/v1/sync-logs
```

### 413 Request Entity Too Large

**Symptom:** Large rsync logs are rejected.

**Fix:** Increase `MAX_REQUEST_BODY_SIZE` in `.env` (default is 10 MB):
```bash
MAX_REQUEST_BODY_SIZE=52428800  # 50 MB
```

### 429 Too Many Requests

**Symptom:** Rate limit exceeded.

**Fix:** Wait for the `Retry-After` period, or increase limits in `.env`:
```bash
RATE_LIMIT_AUTHENTICATED=120/minute
```

## Metrics & Monitoring

### /metrics returns empty data

**Symptom:** Prometheus scraping works but no sync metrics appear.

**Cause:** No sync logs have been submitted yet. Sync metrics are only populated after the first `POST /api/v1/sync-logs` request.

### Retention not cleaning up old logs

**Symptom:** Old sync logs are not being deleted.

1. Check that retention is enabled:
   ```bash
   # In .env
   DATA_RETENTION_DAYS=90  # Must be > 0
   ```

2. Check application logs for retention task output:
   ```bash
   docker-compose logs app | grep retention
   ```

3. The cleanup runs on a schedule (`RETENTION_CLEANUP_INTERVAL_HOURS`, default 24 hours). It does not run immediately on startup.

## Common Errors

### "rsync output could not be parsed"

**Cause:** The `raw_content` field doesn't contain recognizable rsync output.

**Fix:** Ensure you're passing the full rsync output including the `--stats` summary:
```bash
rsync -avz --stats /source/ /dest/ 2>&1
```

### Health check failing

Verify the application is running:
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

If it fails, check Docker logs or restart:
```bash
docker-compose restart app
```
