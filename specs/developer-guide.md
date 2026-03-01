# Spec: Developer Guide

**Version:** 0.1.0
**Created:** 2026-03-01
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Add a comprehensive "Development" section to the README that replaces the existing "Local Development" and "Contributing" sections. The new section covers the full developer workflow: environment setup, dependencies, running the app, linting, formatting, testing (unit + e2e), pre-commit hooks, and contribution guidelines. Targets Python 3.13.

### User Story

As a new contributor, I want clear step-by-step setup instructions in the README, so that I can clone the repo and have a working dev environment with all quality tooling configured in under 10 minutes.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | README contains a "Development" section that replaces the existing "Local Development" and "Contributing" sections | Must |
| AC-002 | Section documents Python 3.13 venv creation and dependency installation | Must |
| AC-003 | Section documents starting PostgreSQL via `docker-compose up -d db` | Must |
| AC-004 | Section documents running the app locally with `uvicorn app.main:app --reload` | Must |
| AC-005 | Section documents `.env` file setup with reference to `.env.example` | Must |
| AC-006 | Section documents linting with `python3 -m ruff check .` and formatting with `python3 -m ruff format .` | Must |
| AC-007 | Section documents running the full test suite with `pytest` and coverage with `pytest --cov=app` | Must |
| AC-008 | Section documents running the e2e Docker test with `./tests/e2e/run-e2e.sh` and notes it is expected before PRs | Must |
| AC-009 | Section documents the pre-commit hook (ruff + pytest) and how it activates automatically | Should |
| AC-010 | Section documents conventional commit format (`feat:`, `fix:`, `docs:`, etc.) | Must |
| AC-011 | Section documents the PR workflow (feature branches off `main`, PR review required) | Must |
| AC-012 | Instructions are accurate — a fresh clone following the steps results in a working dev environment | Must |
| AC-013 | Section is well-organized with clear sub-headings for each topic | Should |

## 3. User Test Cases

### TC-001: Fresh clone to working dev environment

**Precondition:** Clean machine with Python 3.13 and Docker installed
**Steps:**
1. Clone the repository
2. Follow the "Development" section instructions sequentially
3. Run `pytest` to execute the test suite
4. Run `python3 -m ruff check .` and `python3 -m ruff format --check .`
**Expected Result:** All tests pass, no lint/format errors
**Screenshot Checkpoint:** N/A (documentation only)
**Maps to:** TBD

### TC-002: E2E test execution from README instructions

**Precondition:** Dev environment set up per TC-001, Docker running
**Steps:**
1. Follow the e2e test instructions in the README
2. Run `./tests/e2e/run-e2e.sh`
**Expected Result:** E2E test passes with "E2E TEST PASSED" output
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-003: Pre-commit hook fires on commit attempt

**Precondition:** Dev environment set up per TC-001
**Steps:**
1. Stage a file change
2. Run `git commit`
**Expected Result:** Pre-commit hook runs ruff format check, ruff lint, and pytest before allowing the commit
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

## 4. Data Model

N/A — this is a documentation-only feature with no data model changes.

## 5. API Contract (if applicable)

N/A — no API changes.

## 6. UI Behavior (if applicable)

N/A — README markdown only.

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| User has Python < 3.11 | Instructions specify Python 3.13; pre-existing Prerequisites section lists Python 3.11+ as minimum |
| User doesn't have Docker | Prerequisites section already lists Docker as required |
| User on Linux vs macOS | Instructions use portable commands (`python3 -m venv`, `source .venv/bin/activate`) |
| Pre-commit hook doesn't exist (fresh clone) | Document that the hook lives in `.git/hooks/` and is not tracked; provide the install command |

## 8. Dependencies

- Existing `.env.example` file (already exists)
- Pre-commit hook in `.git/hooks/pre-commit` (just created this session)
- E2E test at `tests/e2e/run-e2e.sh` (just created this session)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-01 | 0.1.0 | Claude | Initial spec from /add:spec interview |
