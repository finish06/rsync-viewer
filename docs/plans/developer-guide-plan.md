# Implementation Plan: Developer Guide

**Spec Version**: 0.1.0
**Created**: 2026-03-01
**Team Size**: Solo
**Estimated Duration**: 1 hour

## Overview

Replace the existing "Local Development" and "Contributing" sections in README.md with a comprehensive "Development" section covering the full contributor workflow: environment setup, dependencies, running the app, linting, formatting, testing (unit + e2e), pre-commit hooks, and contribution conventions.

## Objectives

- Provide a single, authoritative onboarding path for new contributors
- Document all quality tooling (ruff, pytest, e2e, pre-commit hook)
- Consolidate scattered setup info into one well-organized section

## Success Criteria

- [ ] All 13 acceptance criteria implemented
- [ ] Instructions are accurate (verified against actual project state)
- [ ] Existing README content preserved (only Local Development + Contributing replaced)
- [ ] All quality gates passing after change

## Acceptance Criteria Analysis

### AC-001–AC-004: Environment Setup (venv, deps, DB, app)
- **Complexity**: Simple
- **Effort**: 15 min
- **Tasks**: Write subsection covering Python 3.13 venv, pip install, docker-compose db, uvicorn
- **Testing**: Follow the instructions yourself to verify accuracy

### AC-005: .env file setup
- **Complexity**: Simple
- **Effort**: 5 min
- **Tasks**: Document `cp .env.example .env` and note key variables to set
- **Dependencies**: `.env.example` already exists

### AC-006: Linting and formatting
- **Complexity**: Simple
- **Effort**: 5 min
- **Tasks**: Document `python3 -m ruff check .` and `python3 -m ruff format .`
- **Note**: Must use `python3 -m ruff` (not bare `ruff`) since ruff is not on PATH

### AC-007: Test suite
- **Complexity**: Simple
- **Effort**: 5 min
- **Tasks**: Document pytest, pytest --cov=app, mention 80% threshold

### AC-008: E2E Docker test
- **Complexity**: Simple
- **Effort**: 5 min
- **Tasks**: Document `./tests/e2e/run-e2e.sh`, note it requires Docker, expected before PRs

### AC-009: Pre-commit hook
- **Complexity**: Simple
- **Effort**: 10 min
- **Tasks**: Document the hook, explain it's in `.git/hooks/` (not tracked by git), provide install command for fresh clones
- **Note**: Hook content must be provided inline or via a script so contributors can install it

### AC-010–AC-011: Commit conventions and PR workflow
- **Complexity**: Simple
- **Effort**: 10 min
- **Tasks**: Document conventional commits, feature branch workflow, PR review requirement

### AC-012: Instructions accuracy
- **Complexity**: Simple
- **Effort**: 5 min (verification pass)
- **Tasks**: Re-read final section against actual project files

### AC-013: Section organization
- **Complexity**: Simple
- **Effort**: Covered by writing clear subsections above

## Implementation Phases

This is a single-phase documentation change. No code, no tests, no migrations.

### Phase 1: Write the Development Section

| Task ID | Description | AC | Effort | Dependencies |
|---------|-------------|------|--------|--------------|
| TASK-001 | Remove "Local Development" section (lines 59–74) and "Contributing" section (lines 226–228) from README.md | AC-001 | 5 min | — |
| TASK-002 | Write "Development" section header and "Prerequisites" subsection | AC-001 | 5 min | TASK-001 |
| TASK-003 | Write "Environment Setup" subsection (venv, deps, .env, DB, run app) | AC-002, AC-003, AC-004, AC-005 | 15 min | TASK-002 |
| TASK-004 | Write "Code Quality" subsection (ruff lint, ruff format) | AC-006 | 5 min | TASK-002 |
| TASK-005 | Write "Running Tests" subsection (pytest, coverage, e2e) | AC-007, AC-008 | 10 min | TASK-002 |
| TASK-006 | Write "Pre-Commit Hook" subsection (what it does, install command) | AC-009 | 10 min | TASK-002 |
| TASK-007 | Write "Contributing" subsection (conventional commits, branch workflow, PR process) | AC-010, AC-011 | 10 min | TASK-002 |
| TASK-008 | Review full section for accuracy against project files | AC-012, AC-013 | 5 min | TASK-003–007 |

**Phase Duration**: ~1 hour
**Blockers**: None

## Effort Summary

| Phase | Estimated Hours | Tasks |
|-------|-----------------|-------|
| Phase 1 | 1h | 8 |
| **Total** | **1h** | **8** |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Instructions don't work on Linux | Low | Medium | Use portable commands (python3 -m, source .venv/bin/activate) |
| Pre-commit hook content drifts from .git/hooks/ | Medium | Low | Provide a `scripts/install-hooks.sh` or inline the hook content |
| README gets too long | Low | Low | Keep subsections concise, link to detailed docs where appropriate |

## Key Decision: Pre-Commit Hook Distribution

The hook lives in `.git/hooks/pre-commit` which is not tracked by git. Options:

**Option A (Recommended):** Add a `scripts/install-hooks.sh` that copies the hook into `.git/hooks/`. Document running it after clone. Simple, explicit.

**Option B:** Commit the hook as `scripts/pre-commit` and tell devs to run `git config core.hooksPath scripts/`. Changes git behavior which may surprise people.

**Decision:** Option A — create `scripts/install-hooks.sh` and document it.

## Deliverables

| File | Action |
|------|--------|
| `README.md` | Edit — replace "Local Development" + "Contributing" with "Development" section |
| `scripts/install-hooks.sh` | Create — installs pre-commit hook for fresh clones |

## Spec Traceability

| Task | Acceptance Criteria |
|------|-------------------|
| TASK-001 | AC-001 |
| TASK-002 | AC-001, AC-013 |
| TASK-003 | AC-002, AC-003, AC-004, AC-005 |
| TASK-004 | AC-006 |
| TASK-005 | AC-007, AC-008 |
| TASK-006 | AC-009 |
| TASK-007 | AC-010, AC-011 |
| TASK-008 | AC-012, AC-013 |

## Next Steps

1. Approve this plan
2. Execute TASK-001 through TASK-008 sequentially
3. Run `python3 -m ruff format --check .` and `python3 -m ruff check .` on result
4. Verify by reading the final README section

## Plan History

- 2026-03-01: Initial plan created
