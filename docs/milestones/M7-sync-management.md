# M7 — Sync Management

**Goal:** Transform rsync-viewer from a passive log viewer into an active sync management platform with on-demand triggering, cron scheduling, and real-time progress tracking
**Status:** LATER
**Appetite:** 3 weeks
**Target Maturity:** beta → ga
**Started:** —
**Completed:** —

## Success Criteria

- [ ] "Run Now" button triggers an rsync sync for a configured source
- [ ] Sync configurations (source, destination, flags, SSH key) stored in DB with full CRUD UI
- [ ] Cron-style schedules with enable/disable toggle and next-run-time display
- [ ] Scheduled syncs execute automatically at configured times
- [ ] Real-time sync progress via WebSocket or SSE
- [ ] Running syncs can be cancelled from the UI
- [ ] Failed syncs retry with configurable count and exponential backoff
- [ ] Sync output captured and stored as a regular sync log entry
- [ ] Command injection prevention on all rsync arguments

## Hill Chart

```
Sync Configurations    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
On-Demand Triggering   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Cron Scheduling        ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Real-Time Progress     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Retry & Cancellation   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Sync Configuration CRUD | specs/sync-scheduling.md | SHAPED | DB models, API, UI for managing sync configs |
| On-Demand Sync Trigger | specs/sync-scheduling.md | SHAPED | "Run Now" button, dry-run mode |
| Cron Scheduling | specs/sync-scheduling.md | SHAPED | APScheduler, cron expression builder, next-run display |
| Real-Time Progress | specs/sync-scheduling.md | SHAPED | WebSocket/SSE for live status updates |
| Retry & Cancellation | specs/sync-scheduling.md | SHAPED | Exponential backoff, process termination |
| Currently Running View | specs/sync-scheduling.md | SHAPED | Active sync dashboard with cancel controls |

## Pre-Milestone Actions

These process improvements should be completed before cycle planning begins:

1. **Promote to Beta maturity** — Evidence score 10/10 (19 specs, 91% coverage, CI/CD, PR workflow, conventional commits, 8 release tags). Run `/add:retro` to formally promote. Beta activates TDD enforcement, agent coordination, and environment-awareness rules.
2. **Fix CI Docker mount drift** — Switch `docker-compose.dev.yml` to bind-mount the entire project root (or add a pre-commit check) so new top-level directories don't silently break CI tests. This has caused failures twice (`.env.example` and `docs/`/`grafana/`).

## Dependencies

- M3 must be complete (error handling for sync failures, logging for execution tracking, security for command injection prevention)
- M4 recommended (performance optimizations help with concurrent sync tracking)
- Failure detection (M2, complete) provides the foundation for failed sync alerting
- New infrastructure dependency: APScheduler or Celery for schedule execution
- New infrastructure dependency: WebSocket support for real-time updates

## Recommended Implementation Order

1. Sync Configuration models + CRUD API + UI (data foundation)
2. On-Demand Sync Trigger (subprocess management, output capture)
3. Retry & Cancellation (extend trigger with resilience)
4. Cron Scheduling (APScheduler integration, cron builder UI)
5. Real-Time Progress (WebSocket/SSE, running syncs dashboard)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Command injection via rsync arguments | High | Critical | Strict argument validation, no shell expansion, allowlist flags |
| SSH key access security | Medium | High | Document required permissions, validate paths, no key content in DB |
| Orphaned processes on app restart | Medium | Medium | Detect orphans on startup, mark as "interrupted" |
| Scheduler reliability (missed jobs) | Low | Medium | APScheduler with persistent job store, catch-up on missed runs |
| WebSocket connection management at scale | Low | Low | Homelab scale is small; SSE as simpler fallback |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| — | — | — | Cycles to be planned when milestone starts |

## Retrospective

—
