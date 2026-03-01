#!/bin/sh
# entrypoint.sh — Validate environment, generate crontab, start cron daemon.
# Runs as root (cron requires it), but sync.sh runs rsync as the 'rsync' user.

set -eu

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

log "Rsync Client starting up"

# Validate required environment variables (AC-edge: missing vars)
MISSING=""
for var in REMOTE_HOST REMOTE_USER REMOTE_PATH RSYNC_VIEWER_URL RSYNC_VIEWER_API_KEY RSYNC_SOURCE_NAME; do
    eval val="\${$var:-}"
    if [ -z "$val" ]; then
        MISSING="$MISSING $var"
    fi
done

if [ -n "$MISSING" ]; then
    log "ERROR: Missing required environment variables:$MISSING"
    log "ERROR: See .env.example for all required variables"
    exit 1
fi

CRON_SCHEDULE="${CRON_SCHEDULE:-0 */6 * * *}"

# Validate cron expression (basic check: 5 fields)
FIELD_COUNT=$(echo "$CRON_SCHEDULE" | awk '{print NF}')
if [ "$FIELD_COUNT" -ne 5 ]; then
    log "ERROR: Invalid CRON_SCHEDULE '$CRON_SCHEDULE' — expected 5 fields (e.g., '0 */6 * * *')"
    exit 1
fi

# Fix SSH key permissions if mounted
if [ -f /home/rsync/.ssh/id_rsa ]; then
    chmod 600 /home/rsync/.ssh/id_rsa
    chown rsync:rsync /home/rsync/.ssh/id_rsa
    log "SSH key found and permissions set"
else
    log "WARN: No SSH key found at /home/rsync/.ssh/id_rsa"
fi

# Generate crontab dynamically from environment (AC-004)
# Export all env vars so cron job inherits them, then run sync as rsync user
ENV_FILE="/tmp/rsync-env.sh"
env | grep -E '^(REMOTE_|RSYNC_|SSH_PORT|SYNC_MODE)' | sed 's/^/export /' > "$ENV_FILE"

CRONTAB_LINE="$CRON_SCHEDULE . $ENV_FILE && su-exec rsync /scripts/sync.sh >> /proc/1/fd/1 2>&1"

echo "$CRONTAB_LINE" | crontab -

log "Crontab installed: $CRON_SCHEDULE"
log "Sync mode: ${SYNC_MODE:-pull}"
log "Remote: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"
log "Viewer URL: ${RSYNC_VIEWER_URL}"
log "Source name: ${RSYNC_SOURCE_NAME}"

# Run an initial sync immediately if requested
if [ "${RUN_ON_START:-false}" = "true" ]; then
    log "RUN_ON_START=true — running initial sync"
    # shellcheck source=/dev/null
    . "$ENV_FILE"
    su-exec rsync /scripts/sync.sh || log "WARN: Initial sync failed (will retry on schedule)"
fi

log "Starting cron daemon (foreground)"
exec crond -f -l 2
