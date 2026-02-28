# Implementation Plan: Rsync Client Docker Compose

**Spec Version**: 0.1.0
**Spec Reference**: specs/rsync-client-compose.md
**Created**: 2026-02-28
**Team Size**: Solo
**Estimated Duration**: 1 day

## Overview

Build a self-contained `examples/rsync-client/` directory with a custom Alpine Docker image, shell scripts for cron-scheduled rsync with automatic log submission, separate compose files for pull and push modes, and user documentation. No changes to the main application — this is a pure client-side artifact that uses the existing API.

## Objectives

- Provide a zero-scripting setup for homelab users to get rsync logs into the dashboard
- Keep the image small (<30MB) and the configuration simple (one `.env` file)
- Handle edge cases gracefully (API down, overlapping syncs, missing SSH keys)

## Success Criteria

- All 14 acceptance criteria implemented
- Docker image builds and is under 30MB
- Both pull and push compose files work against a running Rsync Viewer instance
- All quality gates passing (lint on shell scripts, documentation complete)
- Manual validation of TC-001 through TC-005

## Acceptance Criteria Analysis

### AC-001: Lightweight Alpine Dockerfile
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: TASK-001
- **Dependencies**: None
- **Risks**: Image size — Alpine packages should keep it under 30MB
- **Testing**: `docker build` + check image size

### AC-002: Pull mode compose file
- **Complexity**: Simple
- **Effort**: 20min
- **Tasks**: TASK-005
- **Dependencies**: TASK-001 (Dockerfile), TASK-003 (entrypoint)
- **Testing**: Manual (TC-001)

### AC-003: Push mode compose file
- **Complexity**: Simple
- **Effort**: 20min
- **Tasks**: TASK-006
- **Dependencies**: TASK-001, TASK-003
- **Testing**: Manual (TC-002)

### AC-004: Dynamic crontab from env var
- **Complexity**: Medium
- **Effort**: 30min
- **Tasks**: TASK-003
- **Dependencies**: TASK-002 (sync script path must be known)
- **Risks**: Cron daemon behavior in Alpine containers
- **Testing**: Build + run with known schedule, verify crontab

### AC-005 + AC-006: Log capture and API submission
- **Complexity**: Medium
- **Effort**: 1h
- **Tasks**: TASK-002
- **Dependencies**: Existing API endpoint
- **Risks**: curl JSON escaping of large rsync output
- **Testing**: Manual (TC-001, TC-002)

### AC-007: SSH key mount
- **Complexity**: Simple
- **Effort**: Included in TASK-001, TASK-005, TASK-006
- **Testing**: Manual with real SSH host

### AC-008: .env.example
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: TASK-004
- **Dependencies**: All env vars defined in spec

### AC-009: Custom rsync args
- **Complexity**: Simple
- **Effort**: Included in TASK-002
- **Testing**: Manual (TC-004)

### AC-010: Custom SSH port
- **Complexity**: Simple
- **Effort**: Included in TASK-002
- **Testing**: Manual (TC-005)

### AC-011: Timestamped stdout logging
- **Complexity**: Simple
- **Effort**: Included in TASK-002
- **Testing**: `docker logs` inspection

### AC-012: README documentation
- **Complexity**: Simple
- **Effort**: 45min
- **Tasks**: TASK-008
- **Dependencies**: All other tasks complete

### AC-013: Graceful API failure
- **Complexity**: Simple
- **Effort**: Included in TASK-002 (curl non-zero exit handling)
- **Testing**: Manual (TC-003)

### AC-014: Non-root user
- **Complexity**: Medium
- **Effort**: Included in TASK-001
- **Risks**: Cron daemons often require root; may need to use supercrond or run cron as root but rsync as non-root
- **Testing**: `docker exec` + `whoami`

## Implementation Phases

### Phase 1: Core Scripts (1.5h)

The sync script and entrypoint are the core logic — everything else wraps them.

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-001 | Write Dockerfile (Alpine + rsync + openssh-client + curl + cron, non-root user setup) | 30min | None | AC-001, AC-007, AC-014 |
| TASK-002 | Write `sync.sh` — rsync execution, output capture, timestamp logging, flock guard, API submission via curl, graceful API failure | 1h | None | AC-005, AC-006, AC-009, AC-010, AC-011, AC-013 |

**Phase Duration**: 1.5h
**Blockers**: None

### Phase 2: Container Orchestration (1h)

Wire the scripts into the container lifecycle and create both compose files.

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-003 | Write `entrypoint.sh` — env var validation, dynamic crontab generation, cron daemon foreground | 30min | TASK-002 | AC-004 |
| TASK-004 | Write `.env.example` with all variables and comments | 15min | None | AC-008 |
| TASK-005 | Write `docker-compose.pull.yml` (pull mode: remote→local, SSH key mount, volume mount) | 10min | TASK-001 | AC-002, AC-007 |
| TASK-006 | Write `docker-compose.push.yml` (push mode: local→remote, SSH key mount, volume mount) | 10min | TASK-001 | AC-003, AC-007 |

**Phase Duration**: 1h
**Blockers**: TASK-001 and TASK-002 must be complete

### Phase 3: Validation & Documentation (1h)

Build, test, and document.

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-007 | Build Docker image, verify size <30MB, test crontab generation, test sync script in isolation | 15min | TASK-001 through TASK-006 | All |
| TASK-008 | Write `README.md` — quick start, env var reference, pull vs push usage, troubleshooting | 45min | TASK-001 through TASK-006 | AC-012 |

**Phase Duration**: 1h
**Blockers**: All implementation tasks complete

## Effort Summary

| Phase | Estimated Hours |
|-------|-----------------|
| Phase 1: Core Scripts | 1.5h |
| Phase 2: Container Orchestration | 1h |
| Phase 3: Validation & Documentation | 1h |
| **Total** | **3.5h** |

## Dependencies

### External Dependencies
- Alpine Linux base image (`alpine:3.21`) — public Docker Hub
- Existing `POST /api/v1/sync-logs` endpoint — already implemented and tested

### Internal Dependencies
- No changes to the main application codebase
- No new Python dependencies
- No database migrations

## Parallelization Strategy

Solo developer — sequential execution. However, TASK-001 and TASK-002 are independent and could be written in parallel if desired.

```
TASK-001 (Dockerfile) ─────────────┐
                                    ├─→ TASK-003 (entrypoint) ─→ TASK-005/006 (compose) ─→ TASK-007 (validate) ─→ TASK-008 (docs)
TASK-002 (sync.sh) ────────────────┘
                                    └─→ TASK-004 (.env.example) ─┘
```

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Alpine cron daemon quirks (no stdout logging) | Medium | Medium | Use busybox crond with `-f -l 2` for foreground + logging, or supercrond |
| curl JSON escaping breaks on special characters in rsync output | Medium | High | Use `jq` for safe JSON construction, or write output to temp file and use `--data-binary` |
| Non-root user can't run cron daemon | Medium | Medium | Run crond as root, but sync.sh runs rsync as non-root via `su-exec` |
| Image size exceeds 30MB | Low | Low | Alpine packages are small; total should be ~15-20MB |
| SSH host key verification blocks first connection | Low | High | Use `StrictHostKeyChecking=accept-new` in SSH config (spec requirement) |

## Testing Strategy

This feature is primarily shell scripts and Docker configuration — no Python code, no unit tests in the traditional sense.

1. **Build Validation** (TASK-007)
   - Docker image builds successfully
   - Image size < 30MB
   - All required binaries present (rsync, ssh, curl, crond, flock)

2. **Script Validation** (TASK-007)
   - Entrypoint validates required env vars and exits on missing
   - Crontab is generated correctly from `CRON_SCHEDULE`
   - sync.sh constructs valid JSON payload
   - sync.sh handles curl failure gracefully

3. **Manual Integration Testing** (TC-001 through TC-005)
   - Pull mode against a real SSH host
   - Push mode against a real SSH host
   - API unreachable scenario
   - Custom rsync args
   - Non-standard SSH port

4. **Quality Gates**
   - `shellcheck` on all `.sh` files (if available)
   - Dockerfile best practices (no `latest` tag, minimal layers)

## Deliverables

### Files
- `examples/rsync-client/Dockerfile`
- `examples/rsync-client/docker-compose.pull.yml`
- `examples/rsync-client/docker-compose.push.yml`
- `examples/rsync-client/.env.example`
- `examples/rsync-client/entrypoint.sh`
- `examples/rsync-client/sync.sh`
- `examples/rsync-client/README.md`

### No Changes To
- Main application code
- Database schema
- Existing tests
- CI/CD pipeline

## Success Metrics

- [ ] All 14 acceptance criteria addressed
- [ ] Docker image builds and is <30MB
- [ ] Pull mode works end-to-end (TC-001)
- [ ] Push mode works end-to-end (TC-002)
- [ ] Graceful API failure (TC-003)
- [ ] Custom args work (TC-004)
- [ ] Custom SSH port works (TC-005)
- [ ] README covers all usage scenarios
- [ ] Shell scripts pass shellcheck (no critical warnings)

## Next Steps

1. Get plan approval
2. Begin Phase 1: Write Dockerfile and sync.sh
3. Phase 2: Entrypoint, .env.example, compose files
4. Phase 3: Build, validate, document
5. Commit to feature branch and create PR

## Plan History

- 2026-02-28: Initial plan created
