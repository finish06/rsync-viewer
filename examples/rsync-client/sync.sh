#!/bin/sh
# sync.sh — Execute rsync, capture output, ship log to Rsync Viewer API.
# Run by cron on the configured schedule. Uses flock to prevent overlapping runs.

set -eu

LOCK_FILE="/tmp/rsync-sync.lock"
MAX_RAW_BYTES=10485760  # 10MB truncation limit

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

# Prevent overlapping runs (AC-edge: concurrent cron triggers)
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log "WARN: Previous sync still running, skipping this cycle"
    exit 0
fi

# Validate required environment variables
for var in REMOTE_HOST REMOTE_USER REMOTE_PATH RSYNC_VIEWER_URL RSYNC_VIEWER_API_KEY RSYNC_SOURCE_NAME; do
    eval val="\${$var:-}"
    if [ -z "$val" ]; then
        log "ERROR: Required variable $var is not set"
        exit 1
    fi
done

RSYNC_ARGS="${RSYNC_ARGS:--avz --stats}"
SSH_PORT="${SSH_PORT:-22}"
SYNC_MODE="${SYNC_MODE:-pull}"

# Build SSH options
SSH_OPTS="-p ${SSH_PORT} -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/home/rsync/.ssh/known_hosts"
if [ -f /home/rsync/.ssh/id_rsa ]; then
    SSH_OPTS="$SSH_OPTS -i /home/rsync/.ssh/id_rsa"
fi

# Record start time
START_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
log "Starting rsync ($SYNC_MODE mode) to ${REMOTE_HOST}:${REMOTE_PATH}"

# Build rsync command based on mode
if [ "$SYNC_MODE" = "push" ]; then
    RSYNC_SRC="/data/"
    RSYNC_DST="${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"
else
    RSYNC_SRC="${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"
    RSYNC_DST="/data/"
fi

# Execute rsync and capture output
TMPFILE=$(mktemp)
RSYNC_EXIT=0
# shellcheck disable=SC2086
rsync $RSYNC_ARGS -e "ssh $SSH_OPTS" "$RSYNC_SRC" "$RSYNC_DST" >"$TMPFILE" 2>&1 || RSYNC_EXIT=$?

END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Read and truncate output if needed
RAW_CONTENT=$(head -c "$MAX_RAW_BYTES" "$TMPFILE")
rm -f "$TMPFILE"

if [ $RSYNC_EXIT -ne 0 ]; then
    log "WARN: rsync exited with code $RSYNC_EXIT"
else
    log "rsync completed successfully"
fi

# Build JSON payload using jq for safe escaping (AC-005, AC-006)
PAYLOAD=$(jq -n \
    --arg source_name "$RSYNC_SOURCE_NAME" \
    --arg start_time "$START_TIME" \
    --arg end_time "$END_TIME" \
    --arg raw_content "$RAW_CONTENT" \
    '{
        source_name: $source_name,
        start_time: $start_time,
        end_time: $end_time,
        raw_content: $raw_content
    }')

# Submit to Rsync Viewer API (AC-013: graceful failure)
log "Submitting log to ${RSYNC_VIEWER_URL}/api/v1/sync-logs"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' \
    -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: ${RSYNC_VIEWER_API_KEY}" \
    -d "$PAYLOAD" \
    --max-time 30 \
    "${RSYNC_VIEWER_URL}/api/v1/sync-logs" 2>/dev/null) || HTTP_CODE="000"

if [ "$HTTP_CODE" = "201" ]; then
    log "Log submitted successfully (HTTP $HTTP_CODE)"
elif [ "$HTTP_CODE" = "000" ]; then
    log "WARN: Could not reach Rsync Viewer API — will retry next cycle"
else
    log "WARN: API returned HTTP $HTTP_CODE — will retry next cycle"
fi

exit 0
