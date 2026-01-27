#!/bin/bash
# Example script to send rsync output to the viewer API
#
# Usage: ./send_sync_log.sh <source_name> <rsync_command>
# Example: ./send_sync_log.sh "Movies" "rsync -avz /source/ /dest/"

set -e

API_URL="${RSYNC_VIEWER_URL:-http://localhost:8000}/api/v1/sync-logs"
API_KEY="${RSYNC_VIEWER_API_KEY:-rsv_dev_key_12345}"
SOURCE_NAME="${1:-Default}"
shift || true

# Capture start time (ISO 8601 format)
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "Starting $SOURCE_NAME sync at $START_TIME"

# Run rsync and capture output
# If no command provided, read from stdin (for piping existing logs)
if [ $# -eq 0 ]; then
    RSYNC_OUTPUT=$(cat)
else
    RSYNC_OUTPUT=$("$@" 2>&1) || true
fi

# Capture end time
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "Sync completed at $END_TIME"
echo "Sending log to $API_URL"

# Send to API using jq to properly escape the content
curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d "$(jq -n \
        --arg source "$SOURCE_NAME" \
        --arg start "$START_TIME" \
        --arg end "$END_TIME" \
        --arg content "$RSYNC_OUTPUT" \
        '{source_name: $source, start_time: $start, end_time: $end, raw_content: $content}')" \
    && echo "Log sent successfully" \
    || echo "Failed to send log"
