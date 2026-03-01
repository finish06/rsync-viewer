# Cycle 13 — Rsync Client Docker Compose

**Milestone:** M10 — Rsync Client & Sync Management
**Maturity:** beta
**Status:** PLANNED
**Started:** TBD
**Completed:** TBD
**Duration Budget:** 1 day

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| Rsync Client Docker Compose | SPECCED | VERIFIED | Agent-1 | ~3.5h | All 14 ACs addressed, Docker image <30MB, both compose files functional, README complete |

## Dependencies & Serialization

No dependencies — single feature, all upstream work complete:
- M9 (Multi-User) — COMPLETE (API key auth)
- `POST /api/v1/sync-logs` endpoint — COMPLETE

Single-threaded execution. Phases advance sequentially per plan.

## Implementation Phases

### Phase 1: Core Scripts (~1.5h)
- **TASK-001:** Write `Dockerfile` — Alpine + rsync + openssh-client + curl + cron, non-root user
- **TASK-002:** Write `sync.sh` — rsync execution, output capture, timestamp logging, flock guard, API submission via curl, graceful API failure

### Phase 2: Container Orchestration (~1h)
- **TASK-003:** Write `entrypoint.sh` — env var validation, dynamic crontab generation, cron daemon foreground
- **TASK-004:** Write `.env.example` — all variables with comments
- **TASK-005:** Write `docker-compose.pull.yml` — pull mode (remote→local)
- **TASK-006:** Write `docker-compose.push.yml` — push mode (local→remote)

### Phase 3: Validation & Documentation (~1h)
- **TASK-007:** Build Docker image, verify size <30MB, test crontab generation
- **TASK-008:** Write `README.md` — quick start, env var reference, pull vs push, troubleshooting

## Validation Criteria

### Per-Item Validation
- AC-001: Alpine image <30MB with rsync, openssh-client, curl, cron
- AC-002: Pull mode compose file works (remote→local)
- AC-003: Push mode compose file works (local→remote)
- AC-004: Entrypoint generates crontab from CRON_SCHEDULE env var
- AC-005: Script captures stdout/stderr and POSTs to API
- AC-006: Payload matches SyncLogCreate schema (source_name, start_time, end_time, raw_content)
- AC-007: SSH key mount via volume
- AC-008: .env.example documents all variables
- AC-009: RSYNC_ARGS env var for custom flags (default: -avz --stats)
- AC-010: SSH_PORT env var (default: 22)
- AC-011: Timestamped stdout logging for docker logs
- AC-012: README.md covers setup, config, pull/push
- AC-013: Graceful API failure (log warning, don't crash)
- AC-014: Non-root user where possible

### Cycle Success Criteria
- [ ] All 14 acceptance criteria addressed
- [ ] Docker image builds and is <30MB
- [ ] Shell scripts pass shellcheck (no critical warnings)
- [ ] README covers all usage scenarios
- [ ] Feature branch with PR ready for human review

## Agent Autonomy & Checkpoints

Autonomous mode. Agent executes full cycle, commits to feature branch, creates PR when done. Human reviews on return.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Alpine cron daemon quirks | Use busybox crond with `-f -l 2` for foreground + logging |
| JSON escaping of rsync output | Use jq for safe JSON construction |
| Non-root user can't run cron | Run crond as root, sync.sh runs rsync as non-root via su-exec |

## Notes

- No changes to the main application codebase
- No new Python dependencies
- No database migrations
- All deliverables go in `examples/rsync-client/`
- Spec: specs/rsync-client-compose.md
- Plan: docs/plans/rsync-client-compose-plan.md
