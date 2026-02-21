# M2 — Notifications

**Goal:** Alert users when syncs fail via webhooks to Home Assistant and Discord
**Status:** IN_PROGRESS
**Appetite:** 1 week
**Target Maturity:** alpha
**Started:** 2026-02-21
**Completed:** —

## Success Criteria

- [ ] Failed sync (non-zero exit code) triggers webhook within 60 seconds
- [ ] Stale sync detection — sources missing expected sync within configured interval trigger alert
- [ ] Home Assistant webhook integration tested and working
- [ ] Discord webhook integration tested and working
- [ ] Notification history viewable in dashboard (timestamp, source, reason, delivery status)
- [ ] Sync source frequency configuration (24h, 7d, 14d, custom) manageable via dashboard

## Hill Chart

```
Failure Detection    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Webhook Service      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Home Assistant       ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Discord Integration  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Failure Detection | — | SHAPED | Non-zero exit code + stale sync (missing expected interval) |
| Webhook Notification Service | — | SHAPED | Configurable endpoints, DB-stored config, background scheduler |
| Home Assistant Integration | — | SHAPED | HA webhook format, tested delivery |
| Discord Integration | — | SHAPED | Discord webhook format, tested delivery |

## Dependencies

- Failure detection must be implemented before webhook service can trigger on failures
- Webhook service must exist before HA/Discord integrations
- Stale sync detection requires sync source frequency config (new DB model)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Background scheduler reliability | Medium | High | Use proven library (APScheduler), health checks |
| Webhook endpoint format changes | Low | Medium | Abstract webhook delivery, easy to update format |
| Stale detection false positives | Medium | Medium | Grace period on intervals, configurable per source |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| — | — | — | — |

## Retrospective

—
