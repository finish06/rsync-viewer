# Spec: GitHub Actions CI Pipeline

**Version:** 0.1.0
**Created:** 2026-02-19
**PRD Reference:** docs/prd.md — M1: Foundation
**Status:** Complete
**Milestone:** M1 — Foundation

## 1. Overview

A GitHub Actions CI pipeline that runs on every pull request targeting `main`. The pipeline lints (ruff), type-checks (mypy), and runs the full test suite with coverage (pytest + PostgreSQL) in a Docker Compose environment. All checks must pass before a PR can be merged (required status checks).

### User Story

As a developer, I want automated quality checks on every PR, so that regressions, lint errors, and type issues are caught before code reaches main.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A GitHub Actions workflow file exists at `.github/workflows/ci.yml` | Must |
| AC-002 | The workflow triggers on pull requests targeting `main` | Must |
| AC-003 | The workflow also triggers on pushes to `main` (catch post-merge issues) | Should |
| AC-004 | The pipeline runs `ruff check .` and fails if there are lint errors | Must |
| AC-005 | The pipeline runs `ruff format --check .` and fails if formatting is wrong | Must |
| AC-006 | The pipeline runs `mypy app/` and fails if there are type errors | Must |
| AC-007 | The pipeline runs `pytest tests/ --cov=app` with a PostgreSQL service and fails if any test fails | Must |
| AC-008 | The pipeline fails if test coverage is below 80% | Must |
| AC-009 | The pipeline uses Python 3.11 to match the production target | Must |
| AC-010 | A `requirements-dev.txt` file exists with dev/test dependencies (ruff, mypy, pytest, pytest-cov, etc.) separated from runtime `requirements.txt` | Must |
| AC-011 | The pipeline uses Docker Compose (`docker-compose.dev.yml`) to run the test suite against a real PostgreSQL instance | Must |
| AC-012 | Pipeline results are visible as GitHub PR status checks | Must |
| AC-013 | The workflow should be configured as a required status check to block merging on failure | Should |

## 3. User Test Cases

### TC-001: PR with Clean Code Passes CI

**Precondition:** A feature branch with passing tests, clean lint, and valid types.
**Steps:**
1. Push a commit to a feature branch
2. Open a PR targeting `main`
3. Observe the GitHub Actions workflow triggers
4. Wait for the workflow to complete
**Expected Result:** All jobs pass (lint, type-check, test). PR shows green checkmarks. PR is mergeable.
**Screenshot Checkpoint:** N/A (GitHub UI)
**Maps to:** TBD

### TC-002: PR with Lint Error Blocks Merge

**Precondition:** A feature branch with a ruff lint violation.
**Steps:**
1. Introduce a lint error (e.g., unused import)
2. Push and open PR
3. Wait for CI to run
**Expected Result:** The lint job fails. PR shows a red X. PR cannot be merged until fixed.
**Screenshot Checkpoint:** N/A (GitHub UI)
**Maps to:** TBD

### TC-003: PR with Failing Test Blocks Merge

**Precondition:** A feature branch with a broken test.
**Steps:**
1. Introduce a failing test assertion
2. Push and open PR
3. Wait for CI to run
**Expected Result:** The test job fails. PR shows a red X. Failure details visible in Actions logs.
**Screenshot Checkpoint:** N/A (GitHub UI)
**Maps to:** TBD

### TC-004: PR with Low Coverage Blocks Merge

**Precondition:** A feature branch where new code lowers coverage below 80%.
**Steps:**
1. Add untested code that drops coverage below threshold
2. Push and open PR
3. Wait for CI to run
**Expected Result:** The test job fails due to coverage threshold. PR shows a red X.
**Screenshot Checkpoint:** N/A (GitHub UI)
**Maps to:** TBD

### TC-005: PR with Type Error Blocks Merge

**Precondition:** A feature branch with a mypy type error.
**Steps:**
1. Introduce a type error (e.g., wrong return type)
2. Push and open PR
3. Wait for CI to run
**Expected Result:** The type-check job fails. PR cannot be merged.
**Screenshot Checkpoint:** N/A (GitHub UI)
**Maps to:** TBD

## 4. Data Model

No database changes required. This feature is purely CI/CD infrastructure.

### Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | GitHub Actions workflow definition |
| `requirements-dev.txt` | Dev/test/lint/type-check dependencies |

## 5. API Contract

N/A — no API changes.

## 6. UI Behavior

N/A — no UI changes. Results are visible in the GitHub PR interface.

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| PR opened from a fork | Workflow should still trigger (with appropriate permissions) |
| Multiple commits pushed rapidly | GitHub Actions runs on the latest commit, cancels in-progress runs for the same PR |
| PostgreSQL service fails to start in CI | Job fails with clear error; retry should resolve transient issues |
| requirements-dev.txt out of sync with what CI needs | CI fails at install step with clear pip error |
| Coverage exactly at 80% | Should pass (threshold is >= 80%) |
| Workflow file has YAML syntax error | GitHub surfaces the error in the Actions tab |

## 8. Dependencies

- GitHub Actions (already configured as CI platform in `.add/config.json`)
- Docker and Docker Compose available in GitHub Actions runners (ubuntu-latest includes these)
- PostgreSQL 16 (via `docker-compose.dev.yml` service)
- Python packages: ruff, mypy, pytest, pytest-cov, pytest-asyncio, httpx

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-19 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
