# Cycle 7 — Beta Promotion, Changelog Viewer, Dev Tooling & M7 Planning

**Milestone:** M6 — Observability (completion + post-milestone work)
**Maturity:** beta (promoted during this cycle)
**Status:** COMPLETE
**Started:** 2026-02-24
**Completed:** 2026-02-24
**Duration Budget:** 1 day

## Work Items

| Feature | Current Pos | Target Pos | Assigned | Est. Effort | Validation |
|---------|-------------|-----------|----------|-------------|------------|
| Beta Promotion | — | DONE | Agent-1 | ~1 hour | Retro completed, config updated, maturity=beta |
| Changelog Viewer | SHAPED | DONE | Agent-1 | ~3 hours | AC-001–AC-010 passing, CSP-compliant toggle, Unreleased filtered |
| Dev Seed Data | SHAPED | DONE | Agent-1 | ~2 hours | AC-001–AC-010 passing, idempotent seeding, 50 logs + webhooks + failures |
| OIDC Authentication Spec & Plan | — | SPECCED | Agent-1 | ~1 hour | Spec with 17 ACs, plan with 23 tasks, M7 milestone created |
| CI Reliability Fixes | — | DONE | Agent-1 | ~1 hour | Lint errors fixed, COVERAGE_FILE=/tmp, ruff format enforced |
| Retention Test Coverage | — | DONE | Agent-1 | ~30 min | retention.py 65% → 96%, 4 new async tests |

## Dependencies & Serialization

```
Beta Promotion (Agent-1)
    ↓
Changelog Viewer (Agent-1)
    ↓
Dev Seed Data (Agent-1)
    ↓
OIDC Spec & Plan (Agent-1) — parallel with CI fixes
CI Reliability Fixes (Agent-1) — parallel with OIDC work
    ↓
Retention Test Coverage (Agent-1)
```

Single-threaded execution. Features advanced sequentially.

## Validation Criteria

### Per-Item Validation

- **Beta Promotion:** Config updated to maturity=beta, retro-3 written, Playwright e2e dropped
- **Changelog Viewer:** Accordion toggle works without CSP violation, Unreleased filtered, external JS for toggle logic, 4 tests passing
- **Dev Seed Data:** `docker-compose.seed.yml` overlay works, Python seed script creates tables + seeds 50 logs/3 dry runs/5 failures/2 webhooks/10 notifications, idempotent on restart
- **OIDC Spec:** 17 acceptance criteria covering auth code flow, auto-create/link, UI, security. Plan with 5 phases and 23 tasks. M7 milestone file created. M7/M8/M9 renumbered in PRD.
- **CI Fixes:** Unused imports removed from seed.py, COVERAGE_FILE env var for read-only mount, ruff format on all new files
- **Retention Tests:** 4 new async tests covering background task startup, cleanup execution, exception handling, and shutdown

### Cycle Success Criteria

- [x] All features reach target position
- [x] Full test suite passes (425 tests)
- [x] Test coverage 89% (above 80% threshold)
- [x] CI pipeline fully green (lint, types, tests, build & push)
- [x] ruff check clean
- [x] mypy clean
- [x] No regressions

## Agent Autonomy & Checkpoints

**Mode:** Balanced (Beta maturity, human available throughout).

- Agent executed features sequentially, committed after each
- Human reviewed CI after pushes
- Human directed squash of lint fix commits

## Notes

- This cycle was the first under Beta maturity after promotion from Alpha
- Changelog viewer required CSP-compliant approach — inline onclick/hx-on violated CSP, solved with external JS using htmx:configRequest event
- Seed data initially tried SQL approach but switched to Python SQLModel script because tables don't exist at Postgres initdb time
- OIDC spec depends on M9 (Multi-User) for User model — documented as critical dependency in plan
- Milestone renumbering: OIDC became new M7, pushing Sync Management to M8 and Multi-User to M9
