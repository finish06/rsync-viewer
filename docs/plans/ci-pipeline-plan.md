# Implementation Plan: GitHub Actions CI Pipeline

**Spec:** specs/ci-pipeline.md v0.1.0
**Created:** 2026-02-19
**Team Size:** Solo
**Estimated Duration:** 2-3 hours

## Overview

Create a GitHub Actions CI workflow that runs lint (ruff), type-check (mypy), and tests (pytest + PostgreSQL via Docker Compose) on every PR targeting main. Add a `requirements-dev.txt` for dev dependencies.

## Implementation Phases

### Phase 1: Dev Dependencies (15min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-001 | Create `requirements-dev.txt` with ruff, mypy, and test deps | 10min | AC-010 |
| TASK-002 | Update `Dockerfile.test` to install dev deps | 5min | AC-010 |

**Files created:** `requirements-dev.txt`
**Files modified:** `Dockerfile.test`

### Phase 2: GitHub Actions Workflow (45min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-003 | Create `.github/workflows/ci.yml` with lint job (ruff check + ruff format --check) | 15min | AC-001, AC-002, AC-003, AC-004, AC-005, AC-009 |
| TASK-004 | Add type-check job (mypy app/) | 10min | AC-006 |
| TASK-005 | Add test job using Docker Compose with PostgreSQL, pytest --cov, and --cov-fail-under=80 | 20min | AC-007, AC-008, AC-011, AC-012 |
| TASK-006 | Add concurrency group to cancel stale runs | 5min | Edge case |

**Files created:** `.github/workflows/ci.yml`

### Phase 3: Fix Lint/Type Issues (30-60min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-007 | Run ruff check locally and fix any lint errors | 15min | AC-004 |
| TASK-008 | Run ruff format --check and fix formatting | 10min | AC-005 |
| TASK-009 | Run mypy app/ and fix type errors | 30min | AC-006 |

**Files modified:** Various app/ files as needed

### Phase 4: Improve Test Coverage (45-60min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-010 | Add tests for HTMX handlers (htmx_sync_table, htmx_charts, htmx_sync_detail) | 30min | AC-008 |
| TASK-011 | Add tests for settings_page and index routes | 15min | AC-008 |
| TASK-012 | Verify coverage >= 80% | 5min | AC-008 |

**Files modified:** `tests/test_api.py` or new test files

## Spec Traceability

| Task | Acceptance Criteria |
|------|-------------------|
| TASK-001, TASK-002 | AC-010 |
| TASK-003 | AC-001, AC-002, AC-003, AC-004, AC-005, AC-009 |
| TASK-004 | AC-006 |
| TASK-005 | AC-007, AC-008, AC-011, AC-012 |
| TASK-007 | AC-004 |
| TASK-008 | AC-005 |
| TASK-009 | AC-006 |
| TASK-010, TASK-011, TASK-012 | AC-008 |

## Notes

- AC-013 (required status check) requires GitHub admin access — queued for human
- The workflow uses Docker Compose in CI to match local dev testing
- Coverage threshold enforced via `--cov-fail-under=80`
