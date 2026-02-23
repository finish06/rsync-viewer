# M2 — Notifications

**Goal:** Alert users when syncs fail via webhooks, with Discord support and a settings UI for managing endpoints
**Status:** COMPLETE
**Appetite:** 1 week
**Target Maturity:** alpha
**Started:** 2026-02-21
**Completed:** 2026-02-22

## Success Criteria

- [x] Failed sync (non-zero exit code) triggers webhook within 60 seconds
- [x] Stale sync detection — sources missing expected sync within configured interval trigger alert
- [x] Discord webhook integration tested and working (PR #6)
- [x] Sync source frequency configuration (24h, 7d, 14d, custom) manageable via dashboard
- [x] Webhook settings UI at `/settings` for add/edit/delete/enable/disable endpoints (PR #8)
- [x] Notification history viewable in dashboard (timestamp, source, reason, delivery status) (PR #9)

## Hill Chart

```
Failure Detection    ████████████████████████████████████  DONE
Webhook Service      ████████████████████████████████████  DONE
Discord Integration  ████████████████████████████████████  DONE (PR #6, merged 2026-02-21)
Webhook Settings UI  ████████████████████████████████████  DONE (PR #8, merged 2026-02-22)
Notification History ████████████████████████████████████  DONE (PR #9, merged 2026-02-22)
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Failure Detection | specs/failure-detection.md | DONE | 31 tests, exit code + stale sync + monitors CRUD |
| Webhook Notification Service | specs/webhook-service.md | DONE | Backend complete, retry + auto-disable + notification log |
| Discord Integration | specs/discord-integration.md | DONE | 26 tests, embeds + source filters + rate limiting, PR #6 merged |
| Webhook Settings UI | specs/webhook-service.md (AC-007) | DONE | 21 tests, full CRUD + toggle + test button, PR #8 merged |
| Notification History | specs/notification-history.md | DONE | 17 tests, HTMX dashboard tab + filters + pagination, PR #9 merged |

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
| cycle-4 | Webhook Settings UI, Notification History | COMPLETE | Settings UI (21 tests, PR #8), Notification History (17 tests, PR #9) |

## Retrospective

**Completed:** 2026-02-22 (5 features across 4 cycles, within 1-week appetite)

**What went well:**
- Clean dependency chain: failure detection → webhook service → Discord → UI → history. Each built naturally on the prior.
- All 5 features shipped with strong test coverage (31 + backend + 26 + 21 + 17 tests).
- Performance optimizations (N+1 queries, webhook.enabled index, DB commit reduction) were addressed inline during implementation rather than deferred.

**What could improve:**
- VERIFIED → DONE promotion was missed at milestone close — features sat at VERIFIED after PR merge instead of being immediately marked DONE.
- The webhook settings UI spec was embedded in the webhook-service spec (AC-007) rather than being its own spec, which made tracking slightly ambiguous.

**Key learnings:**
- APScheduler integration for stale sync detection worked well and was straightforward.
- Discord rate limit handling (429 + Retry-After) needed explicit testing — easy to miss.
- HTMX partial loading for notification history tab was a clean pattern worth reusing.
