# M2 — Notifications

**Goal:** Alert users when syncs fail via webhooks, with Discord support and a settings UI for managing endpoints
**Status:** IN_PROGRESS
**Appetite:** 1 week
**Target Maturity:** alpha
**Started:** 2026-02-21
**Completed:** —

## Success Criteria

- [x] Failed sync (non-zero exit code) triggers webhook within 60 seconds
- [x] Stale sync detection — sources missing expected sync within configured interval trigger alert
- [x] Discord webhook integration tested and working (PR #6)
- [x] Sync source frequency configuration (24h, 7d, 14d, custom) manageable via dashboard
- [x] Webhook settings UI at `/settings` for add/edit/delete/enable/disable endpoints (PR #8)
- [ ] Notification history viewable in dashboard (timestamp, source, reason, delivery status)

## Hill Chart

```
Failure Detection    ████████████████████████████████████  DONE
Webhook Service      ████████████████████████████████████  DONE
Discord Integration  ██████████████████████████████████░░  VERIFIED (PR #6)
Webhook Settings UI  ██████████████████████████████████░░  VERIFIED (PR #8)
Notification History ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Failure Detection | specs/failure-detection.md | DONE | 31 tests, exit code + stale sync + monitors CRUD |
| Webhook Notification Service | specs/webhook-service.md | DONE | Backend complete, retry + auto-disable + notification log |
| Discord Integration | specs/discord-integration.md | VERIFIED | 26 tests, embeds + source filters + rate limiting, PR #6 |
| Webhook Settings UI | specs/webhook-service.md (AC-007) | VERIFIED | 21 tests, full CRUD + toggle + test button, PR #8 |
| Notification History | — | SHAPED | Dashboard view of delivery history from notification_log table |

## Dependencies

- Failure detection must be implemented before webhook service can trigger on failures (**done**)
- Webhook service must exist before Discord integration (**done**)
- Webhook backend must exist before settings UI can be built (**done**)
- Notification log table must exist before history dashboard (**done** — table exists)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Background scheduler reliability | Medium | High | Use proven library (APScheduler), health checks |
| Webhook endpoint format changes | Low | Medium | Abstract webhook delivery, easy to update format |
| Stale detection false positives | Medium | Medium | Grace period on intervals, configurable per source |
| HTMX form complexity for Discord options | Low | Medium | Progressive disclosure — show Discord fields only when type=discord |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| cycle-1 | Failure Detection | COMPLETE | 31 tests, 94% coverage, all ACs passing |
| cycle-2 | Webhook Service (backend) | COMPLETE | Retry, auto-disable, notification log, optimized queries |
| cycle-3 | Discord Integration | COMPLETE | 26 tests, PR #6, embeds + source filters + rate limiting |
| cycle-4 | Webhook Settings UI, Notification History | PLANNED | HTMX UI for managing webhooks + delivery history view |

## Retrospective

—
