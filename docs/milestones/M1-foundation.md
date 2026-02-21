# M1 — Foundation

**Goal:** Establish CI/CD pipeline, improve test coverage, adopt conventional commits, stabilize existing features
**Status:** IN_PROGRESS
**Appetite:** 1-2 weeks
**Target Maturity:** poc → alpha
**Started:** 2026-02-19

## Success Criteria

- [x] GitHub Actions runs on every PR
- [x] Test coverage >= 80% (currently 92%)
- [x] All existing tests pass in CI (132 passing)
- [x] Conventional commit format adopted
- [x] Comprehensive error handling with consistent response format
- [x] Structured logging with request/response tracking

## Hill Chart

```
CI Pipeline         ████████████████████████████████████  DONE — merged, running on PRs
Error Handling      ████████████████████████████████████  DONE — structured errors with codes
Structured Logging  ████████████████████████████████████  DONE — JSON logging with request tracking
Dark Mode           ████████████████████████████████████  DONE — light/dark/system toggle
Date Range Select   ████████████████████████████████████  DONE — quick select + custom date + load all
Average Xfer Rate   ██████████████████████████████████░░  VERIFIED — implemented, tests pass, needs commit
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| CI Pipeline | specs/ci-pipeline.md | DONE | GitHub Actions: lint, type check, tests |
| Error Handling | specs/error-handling.md | DONE | Structured error codes, validation wrapping |
| Structured Logging | specs/structured-logging.md | DONE | JSON logs, request tracking, log levels |
| Dark Mode | specs/dark-mode.md | DONE | Light/dark/system theme toggle |
| Date Range Quick Select | specs/date-range-quick-select.md | DONE | 7d/30d/max/custom + load all |
| Average Transfer Rate | specs/average-transfer-rate.md | VERIFIED | format_rate filter, table + modal |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| Pre-ADD | CI Pipeline, Error Handling, Structured Logging, Dark Mode | COMPLETE | Implemented before formal cycle tracking |
| cycle-1 | Date Range Quick Select, Average Transfer Rate | IN_PROGRESS | First tracked cycle |

## Risk Assessment

| Risk | Status |
|------|--------|
| Coverage below 80% | RESOLVED — at 92% |
| CI not configured | RESOLVED — GitHub Actions running |

## Retrospective

_To be filled at milestone completion._
