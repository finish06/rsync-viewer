#!/usr/bin/env bash
# run-e2e.sh — Build, run, and verify the rsync-client → hub e2e pipeline.
# Usage: ./tests/e2e/run-e2e.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.e2e.yml"
PROJECT="rsync-e2e"
HUB_URL="http://localhost:18741"
API_KEY="e2e_test_key_abcdef123456"
SOURCE_NAME="e2e-test-source"
MAX_WAIT=120

log() { echo "[e2e] $(date '+%H:%M:%S') $*"; }
fail() { log "FAIL: $*"; exit 1; }

# Cleanup on exit
cleanup() {
    log "Tearing down e2e stack..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" down -v --remove-orphans 2>/dev/null || true
}
trap cleanup EXIT

# ── Build & Start ──────────────────────────────────────────────────
log "Building and starting e2e stack..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d --build

# ── Wait for hub health ───────────────────────────────────────────
log "Waiting for hub to become healthy (max ${MAX_WAIT}s)..."
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    if curl -sf "$HUB_URL/health" >/dev/null 2>&1; then
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
if [ $elapsed -ge $MAX_WAIT ]; then
    log "Hub logs:"
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" logs app 2>&1 | tail -30
    fail "Hub did not become healthy within ${MAX_WAIT}s"
fi
log "Hub is healthy"

# ── Wait for client sync ──────────────────────────────────────────
log "Waiting for client to complete sync (max ${MAX_WAIT}s)..."
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    if docker compose -f "$COMPOSE_FILE" -p "$PROJECT" logs rsync-client 2>&1 | grep -q "Log submitted successfully"; then
        break
    fi
    sleep 3
    elapsed=$((elapsed + 3))
done
if [ $elapsed -ge $MAX_WAIT ]; then
    log "Client logs:"
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" logs rsync-client 2>&1 | tail -30
    fail "Client did not report successful submission within ${MAX_WAIT}s"
fi
log "Client reports successful log submission"

# ── Verify sync log in hub ────────────────────────────────────────
RESPONSE=$(curl -sf \
    -H "X-API-Key: $API_KEY" \
    "$HUB_URL/api/v1/sync-logs?source_name=$SOURCE_NAME&limit=5") \
    || fail "GET /api/v1/sync-logs returned non-200"

# Parse with python3 (available on macOS + Linux, no jq dependency on host)
ITEM_COUNT=$(python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
items = data.get('items', [])
print(len(items))
" <<< "$RESPONSE")

if [ "$ITEM_COUNT" -lt 1 ]; then
    fail "Expected at least 1 sync log for source '$SOURCE_NAME', got $ITEM_COUNT"
fi
log "Found $ITEM_COUNT sync log(s) for source '$SOURCE_NAME'"

# Extract fields from first item
python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
item = data['items'][0]

source = item['source_name']
file_count = item.get('file_count') or 0
bytes_recv = item.get('bytes_received') or 0
status = item['status']
is_dry_run = item.get('is_dry_run', False)

print(f'  source_name: {source}')
print(f'  file_count: {file_count}')
print(f'  bytes_received: {bytes_recv}')
print(f'  status: {status}')
print(f'  is_dry_run: {is_dry_run}')

errors = []
if source != '$SOURCE_NAME':
    errors.append(f'source_name mismatch: expected $SOURCE_NAME, got {source}')
if file_count < 1:
    errors.append(f'file_count too low: {file_count}')
if bytes_recv <= 0:
    errors.append(f'bytes_received should be > 0, got {bytes_recv}')
if status != 'completed':
    errors.append(f'status should be completed, got {status}')
if is_dry_run:
    errors.append('is_dry_run should be False')

if errors:
    for e in errors:
        print(f'  ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" <<< "$RESPONSE" || fail "Sync log field assertions failed"

# ── Verify detail endpoint (raw_content + file_list) ──────────────
LOG_ID=$(python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
print(data['items'][0]['id'])
" <<< "$RESPONSE")

DETAIL=$(curl -sf \
    -H "X-API-Key: $API_KEY" \
    "$HUB_URL/api/v1/sync-logs/$LOG_ID") \
    || fail "GET /api/v1/sync-logs/$LOG_ID returned non-200"

python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
raw = data.get('raw_content', '')
files = data.get('file_list') or []
print(f'  raw_content length: {len(raw)} chars')
print(f'  file_list entries: {len(files)}')
if len(raw) < 10:
    print('  ERROR: raw_content too short', file=sys.stderr)
    sys.exit(1)
" <<< "$DETAIL" || fail "Detail endpoint assertions failed"

log "E2E TEST PASSED"
