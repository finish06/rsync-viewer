#!/bin/bash

PIDFILE=./moviesSync.pid
OUTPUT=./moviesSync.log
API_URL="${RSYNC_VIEWER_URL:-http://localhost:8000}/api/v1/sync-logs"
API_KEY="${RSYNC_VIEWER_API_KEY:-rsv_dev_key_12345}"

# Delete old log
rm -rf $OUTPUT

echo "Starting Movies Sync" >> $OUTPUT

# Check for existing process
if [ -f $PIDFILE ]; then
  PID=$(cat $PIDFILE)
  if ps -p $PID > /dev/null 2>&1; then
    echo "Process already running" >> $OUTPUT
    exit 1
  fi
fi

# Create PID file
echo $$ > $PIDFILE
if [ $? -ne 0 ]; then
  echo "Could not create PID file" >> $OUTPUT
  exit 1
fi

# Capture start time in ISO 8601 format
start_time=$(date -Is)
echo "Process started at: $start_time" >> $OUTPUT

if ping -c 1 192.168.1.37 > /dev/null; then
	echo "Beginning Movies transfer" >> $OUTPUT
	rsync -avzI --delete-after --bwlimit=100000 --size-only --no-owner --no-group --omit-dir-times --human-readable --no-perms --fuzzy finish06@192.168.1.37:/mnt/media/movies/ /mnt/storage1/Media/Movies/ >> $OUTPUT
else
	echo "Movies transfer failed" >> $OUTPUT
fi

# Capture end time in ISO 8601 format
end_time=$(date -Is)
echo "Process ended at: $end_time" >> $OUTPUT

# Send log to rsync-viewer API
RSYNC_OUTPUT=$(cat "$OUTPUT")
curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d "$(jq -n \
        --arg source "Movies" \
        --arg starttime "$start_time" \
        --arg endtime "$end_time" \
        --arg content "$RSYNC_OUTPUT" \
        '{source_name: $source, start_time: $starttime, end_time: $endtime, raw_content: $content}')" \
    && echo "Log sent to rsync-viewer" >> $OUTPUT \
    || echo "Failed to send log to rsync-viewer" >> $OUTPUT

rm $PIDFILE
