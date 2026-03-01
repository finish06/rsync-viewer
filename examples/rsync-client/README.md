# Rsync Client for Rsync Viewer

A lightweight Docker container that runs rsync on a cron schedule and automatically ships logs to your [Rsync Viewer](https://github.com/finish06/rsync-viewer) instance.

## Quick Start

```bash
# 1. Clone or copy this directory
cd examples/rsync-client

# 2. Configure
cp .env.example .env
# Edit .env with your settings (remote host, API key, etc.)

# 3. Run (pull mode — sync files FROM remote TO local)
docker compose -f docker-compose.pull.yml up -d

# Or push mode — sync files FROM local TO remote
docker compose -f docker-compose.push.yml up -d
```

## How It Works

```
┌─────────────────┐         rsync over SSH         ┌──────────────┐
│  Rsync Client   │◄──────────────────────────────►│ Remote Server │
│  (this container)│                                └──────────────┘
│                 │
│  cron → rsync   │        POST /api/v1/sync-logs   ┌──────────────┐
│  capture output ├────────────────────────────────►│ Rsync Viewer  │
│  ship to API    │                                 │  (dashboard)  │
└─────────────────┘                                 └──────────────┘
```

1. Cron triggers rsync on your configured schedule
2. rsync runs against the remote server over SSH
3. Output is captured (stdout + stderr)
4. A JSON payload is POSTed to your Rsync Viewer API
5. The log appears in your dashboard with parsed statistics

## Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `REMOTE_HOST` | Remote SSH hostname or IP | `192.168.1.100` |
| `REMOTE_USER` | SSH username | `backup` |
| `REMOTE_PATH` | Path on the remote server | `/mnt/data/backups/` |
| `RSYNC_VIEWER_URL` | Your Rsync Viewer instance URL | `http://192.168.1.50:8000` |
| `RSYNC_VIEWER_API_KEY` | API key from Rsync Viewer | `rsv_abc123...` |
| `RSYNC_SOURCE_NAME` | Name shown in the dashboard | `media-backup` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CRON_SCHEDULE` | `0 */6 * * *` | Cron expression (every 6 hours) |
| `RSYNC_ARGS` | `-avz --stats` | Custom rsync flags |
| `SSH_PORT` | `22` | SSH port on the remote server |
| `RUN_ON_START` | `false` | Run a sync immediately on container start |

### Cron Schedule Examples

| Schedule | Expression |
|----------|-----------|
| Every 5 minutes | `*/5 * * * *` |
| Every hour | `0 * * * *` |
| Every 6 hours | `0 */6 * * *` |
| Daily at 2 AM | `0 2 * * *` |
| Weekly on Sunday at midnight | `0 0 * * 0` |

## Pull Mode vs Push Mode

### Pull Mode (`docker-compose.pull.yml`)

Downloads files **from** the remote server **to** a local directory.

```
Remote Server:/mnt/backups/  →  ./data/
```

The local `./data/` directory is mounted read-write. Use this when the remote server is the source of truth.

### Push Mode (`docker-compose.push.yml`)

Uploads files **from** a local directory **to** the remote server.

```
./data/  →  Remote Server:/mnt/backups/
```

The local `./data/` directory is mounted read-only. Use this when the local machine is the source of truth.

## SSH Setup

The container needs SSH access to the remote server. Mount your SSH private key:

```yaml
volumes:
  - ~/.ssh/id_rsa:/home/rsync/.ssh/id_rsa:ro
```

The container automatically:
- Sets correct permissions (600) on the key
- Uses `StrictHostKeyChecking=accept-new` for first connections (homelab-appropriate)

### Using a Different Key

To use a specific key file, change the volume mount:

```yaml
volumes:
  - /path/to/my-backup-key:/home/rsync/.ssh/id_rsa:ro
```

### Setting Up SSH Key Auth on the Remote

```bash
# On your local machine, copy your public key to the remote
ssh-copy-id -i ~/.ssh/id_rsa backup@192.168.1.100
```

## Custom Rsync Arguments

Override the default `-avz --stats` flags via `RSYNC_ARGS`:

```env
# Delete files on destination that don't exist on source
RSYNC_ARGS=-avz --stats --delete

# Exclude certain patterns
RSYNC_ARGS=-avz --stats --exclude='.DS_Store' --exclude='*.tmp'

# Bandwidth limit (500 KB/s)
RSYNC_ARGS=-avz --stats --bwlimit=500
```

## Monitoring

### Container Logs

All sync activity is logged with timestamps to stdout:

```bash
docker logs rsync-pull
# [2026-02-28T10:00:00Z] Starting rsync (pull mode) to 192.168.1.100:/mnt/backups/
# [2026-02-28T10:00:30Z] rsync completed successfully
# [2026-02-28T10:00:30Z] Submitting log to http://192.168.1.50:8000/api/v1/sync-logs
# [2026-02-28T10:00:31Z] Log submitted successfully (HTTP 201)
```

### Dashboard

After each sync, a log entry appears in your Rsync Viewer dashboard with:
- Transfer statistics (bytes sent/received, file count)
- Duration and average transfer rate
- Full raw rsync output (viewable in detail modal)

## Troubleshooting

### Container exits immediately

Check the logs for missing environment variables:

```bash
docker logs rsync-pull
# ERROR: Missing required environment variables: RSYNC_VIEWER_API_KEY
```

### SSH connection refused

1. Verify the remote host is reachable: `docker exec rsync-pull ssh -p 22 backup@192.168.1.100 echo ok`
2. Check the SSH key is mounted: `docker exec rsync-pull ls -la /home/rsync/.ssh/`
3. Verify the SSH port matches `SSH_PORT`

### Logs not appearing in dashboard

1. Check the container logs for API submission errors
2. Verify `RSYNC_VIEWER_URL` is reachable from the container
3. Verify the API key is valid (test in Rsync Viewer Settings > API Keys)
4. The container handles API downtime gracefully — logs a warning and retries next cycle

### Overlapping syncs

The sync script uses `flock` to prevent overlapping runs. If a sync is still running when the next cron trigger fires, it's skipped with a warning in the logs.

## Image Details

- **Base:** Alpine 3.21
- **Size:** ~8 MB
- **Packages:** rsync, openssh-client, curl, jq, flock, su-exec
- **User:** Runs cron as root (required), rsync as non-root `rsync` user
