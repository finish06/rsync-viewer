# Rsync Log Ingestion Guide

This guide explains how to send rsync synchronization logs to Rsync Log Viewer for parsing and visualization.

## API Endpoint

```
POST /api/v1/sync-logs
Content-Type: application/json
X-API-Key: <your-api-key>
```

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_name` | string | Yes | Identifier for this sync source |
| `start_time` | ISO 8601 datetime | Yes | When the sync started |
| `end_time` | ISO 8601 datetime | Yes | When the sync ended |
| `raw_content` | string | Yes | Raw rsync output |
| `exit_code` | integer | No | rsync exit code (0 = success) |
| `is_dry_run` | boolean | No | Whether this was a dry run (default: false) |

### Example: curl

```bash
curl -X POST http://localhost:8000/api/v1/sync-logs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: rsv_dev_key" \
  -d '{
    "source_name": "nightly-backup",
    "start_time": "2026-01-15T02:00:00Z",
    "end_time": "2026-01-15T02:05:30Z",
    "raw_content": "sending incremental file list\nphoto.jpg\n\nsent 1,234 bytes  received 5,678 bytes  2,304.00 bytes/sec\ntotal size is 10,000  speedup is 1.45",
    "exit_code": 0
  }'
```

### Response

```json
{
  "id": "a1b2c3d4-...",
  "source_name": "nightly-backup",
  "start_time": "2026-01-15T02:00:00Z",
  "end_time": "2026-01-15T02:05:30Z",
  "bytes_sent": 1234,
  "bytes_received": 5678,
  "file_count": 1,
  "exit_code": 0,
  "status": "completed"
}
```

## Bash Script Integration

Wrap your rsync command in a script that captures the output and sends it to the API.

### Basic Script

```bash
#!/usr/bin/env bash
# rsync-and-report.sh — Run rsync and report results to Rsync Log Viewer

set -euo pipefail

SOURCE="/path/to/source/"
DEST="/path/to/destination/"
API_URL="http://localhost:8000/api/v1/sync-logs"
API_KEY="rsv_dev_key"
SOURCE_NAME="my-backup"

# Capture timestamps
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Run rsync and capture output
RSYNC_OUTPUT=$(rsync -avz --stats "$SOURCE" "$DEST" 2>&1) || true
EXIT_CODE=$?

END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Escape the output for JSON
ESCAPED_OUTPUT=$(echo "$RSYNC_OUTPUT" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')

# Send to Rsync Log Viewer
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{
    \"source_name\": \"$SOURCE_NAME\",
    \"start_time\": \"$START_TIME\",
    \"end_time\": \"$END_TIME\",
    \"raw_content\": $ESCAPED_OUTPUT,
    \"exit_code\": $EXIT_CODE
  }"
```

### Cron Integration

Add the script to your crontab for scheduled syncs:

```bash
# Run backup every night at 2 AM and report to Rsync Log Viewer
0 2 * * * /opt/scripts/rsync-and-report.sh >> /var/log/rsync-report.log 2>&1
```

### Dry Run Support

To log dry runs, add the `--dry-run` flag to rsync and set `is_dry_run` in the payload:

```bash
RSYNC_OUTPUT=$(rsync -avz --dry-run --stats "$SOURCE" "$DEST" 2>&1) || true

# Add is_dry_run to the JSON payload
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{
    \"source_name\": \"$SOURCE_NAME\",
    \"start_time\": \"$START_TIME\",
    \"end_time\": \"$END_TIME\",
    \"raw_content\": $ESCAPED_OUTPUT,
    \"exit_code\": $EXIT_CODE,
    \"is_dry_run\": true
  }"
```

## rsync Flags for Best Results

For the parser to extract the most data, include `--stats` in your rsync command:

```bash
rsync -avz --stats /source/ /dest/
```

The parser extracts:
- Bytes sent and received
- Total file size
- Transfer speed
- Speedup ratio
- File count and file list
- Dry run detection

## Authentication

All API endpoints require an `X-API-Key` header. The default development key is set via the `DEFAULT_API_KEY` environment variable. For production, generate a secure key:

```bash
python3 -c "import secrets; print('rsv_' + secrets.token_urlsafe(24))"
```

## Rate Limits

The API enforces rate limits:
- **Authenticated requests:** 60 per minute (default)
- **Unauthenticated requests:** 20 per minute (default)

If you exceed the limit, the API returns `429 Too Many Requests` with a `Retry-After` header.
