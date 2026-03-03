# M10 — Rsync Client & Sync Management

**Goal:** Provide decentralized rsync client containers that run at the edge and ship logs to the central Rsync Viewer hub. The viewer is always the observer, never the executor.
**Status:** COMPLETE
**Appetite:** 1 week
**Target Maturity:** beta → ga
**Started:** 2026-02-28
**Completed:** 2026-03-03

## Architecture

Rsync Viewer follows a **hub-and-spoke model**:
- **Hub (this app):** Receives logs via API, parses statistics, visualizes trends, sends alerts
- **Spokes (rsync clients):** Lightweight Docker containers running rsync on a cron schedule at the edge, shipping output to the hub

The viewer never runs rsync directly. Users deploy client containers alongside their data, configure the remote host and viewer URL, and logs flow in automatically.

## Success Criteria

- [x] Custom Alpine Docker image (<30MB) with rsync + cron + curl
- [x] Pull mode and push mode compose examples work end-to-end
- [x] Logs appear in the Rsync Viewer dashboard automatically after sync
- [x] README covers setup, configuration, and troubleshooting
- [x] Graceful handling of API downtime (no crash, retry next cycle)

## Hill Chart

```
Rsync Client Docker Compose  ████████████████████████████████████  DONE
Synthetic Monitoring         ████████████████████████████████████  DONE
Monitoring Setup Wizard      ████████████████████████████████████  DONE
Alembic Migrations           ████████████████████████████████████  DONE
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Rsync Client Docker Compose | specs/rsync-client-compose.md | DONE | Alpine image, pull/push modes, cron schedule, log shipping |
| Synthetic Monitoring | specs/synthetic-monitoring.md | DONE | Background health check, Prometheus metrics, webhook alerts |
| Monitoring Setup Wizard | specs/monitoring-setup-wizard.md | DONE | Settings UI compose generator, auto-provisioned API keys |
| Alembic Migrations | specs/alembic-migrations.md | DONE | Versioned schema migrations, auto-upgrade on startup |

## Dependencies

- M9 (Multi-User) — COMPLETE (API key auth required for log submission)
- Existing `POST /api/v1/sync-logs` endpoint — COMPLETE

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Alpine cron daemon quirks | Medium | Medium | Use busybox crond in foreground mode |
| JSON escaping of rsync output | Medium | High | Use jq for safe JSON construction |

## Superseded

This milestone merges the original M10 (Sync Management) and M12 (Rsync Client Distribution). The original M10 envisioned the viewer running rsync directly — that approach was replaced with the decentralized client model. Key changes:
- Dropped: APScheduler, subprocess management, WebSocket progress, command injection prevention (viewer doesn't execute rsync)
- Kept: Cron scheduling (moved to client container), log capture and submission
- Added: Client Docker image, compose examples, SSH key mounting, graceful API failure

The old `specs/sync-scheduling.md` is superseded by `specs/rsync-client-compose.md`.

## Plan

See `docs/plans/rsync-client-compose-plan.md` for full implementation plan.

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| cycle-13 | Rsync Client Docker Compose (SPECCED→VERIFIED) | COMPLETE | Delivered in v1.11.0 |

## Retrospective

—
