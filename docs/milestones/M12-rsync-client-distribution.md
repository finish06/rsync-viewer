# Milestone: M12 — Rsync Client Distribution

**Goal:** Provide ready-to-use Docker Compose examples so users can deploy rsync containers that automatically ship logs to their Rsync Viewer instance.

**Target Maturity:** beta → ga
**Status:** LATER
**Appetite:** 1 day

## Success Criteria

- [ ] Custom Alpine Docker image (<30MB) with rsync + cron + curl
- [ ] Pull mode and push mode compose examples work end-to-end
- [ ] Logs appear in the Rsync Viewer dashboard automatically after sync
- [ ] README covers setup, configuration, and troubleshooting
- [ ] Graceful handling of API downtime (no crash, retry next cycle)

## Features

| Feature | Spec | Position |
|---------|------|----------|
| Rsync Client Docker Compose | specs/rsync-client-compose.md | SPECCED |

## Dependencies

- M9 (Multi-User) — COMPLETE (API key auth required for log submission)
- Existing `POST /api/v1/sync-logs` endpoint — COMPLETE

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Alpine cron daemon quirks | Medium | Medium | Use busybox crond in foreground mode |
| JSON escaping of rsync output | Medium | High | Use jq for safe construction |

## Plan

See `docs/plans/rsync-client-compose-plan.md` for full implementation plan.
