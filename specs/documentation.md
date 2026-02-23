# Spec: Project Documentation

**Version:** 0.1.0
**Created:** 2026-02-22
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Create comprehensive documentation for the rsync-viewer project covering setup guides, architecture overview, and operational procedures to enable easier onboarding, maintenance, and usage.

### User Story

As a new developer or self-hoster, I want clear documentation covering setup, architecture, and operations, so that I can deploy and maintain rsync-viewer without needing to read the source code.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A development environment setup guide exists in `docs/` that covers prerequisites, local dev setup, and Docker deployment | Must |
| AC-002 | All environment variables are documented with descriptions, defaults, and examples in an environment variable reference | Must |
| AC-003 | A system architecture diagram exists showing component relationships (FastAPI, PostgreSQL, HTMX frontend, webhook subsystem) | Must |
| AC-004 | Database schema documentation describes all tables, fields, types, and relationships | Must |
| AC-005 | Data flow documentation describes the path from rsync output submission to parsed storage to dashboard display | Must |
| AC-006 | An rsync log ingestion configuration guide explains how to integrate rsync scripts with the API | Should |
| AC-007 | A troubleshooting guide covers common issues (DB connection failures, parsing errors, Docker networking) | Should |
| AC-008 | A new developer can set up the project using only the documentation (no external help needed) | Must |

## 3. User Test Cases

### TC-001: New developer setup

**Precondition:** Fresh development machine with Docker installed
**Steps:**
1. Clone the repository
2. Follow the setup guide step by step
3. Run the application locally
4. Submit a test rsync log via API
**Expected Result:** Application is running, log is parsed and visible in the dashboard. No steps required undocumented knowledge.
**Screenshot Checkpoint:** N/A (documentation)
**Maps to:** AC-001, AC-002, AC-008

### TC-002: Environment variable reference completeness

**Precondition:** Application source code available
**Steps:**
1. Grep codebase for all environment variable references
2. Compare against documented variables
**Expected Result:** Every environment variable used in the code is documented with description, default value, and example.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-002

### TC-003: Architecture comprehension

**Precondition:** Architecture documentation exists
**Steps:**
1. Read the architecture overview
2. Identify all major components and their interactions
3. Trace the data flow from API submission to dashboard display
**Expected Result:** Reader can describe the system architecture, identify each component's role, and explain the data flow without reading source code.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-003, AC-004, AC-005

## 4. Data Model

No new data models. This spec covers documentation artifacts only.

## 5. API Contract

No new API endpoints. Existing FastAPI auto-generated OpenAPI/Swagger docs are already available at `/docs`.

## 6. Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| Setup Guide | `docs/setup.md` | Development environment setup, Docker deployment, prerequisites |
| Environment Reference | `docs/environment-variables.md` | All env vars with descriptions, defaults, examples |
| Architecture Overview | `docs/architecture.md` | System diagram, component descriptions, tech stack |
| Database Schema | `docs/database-schema.md` | Tables, fields, types, relationships |
| Data Flow | Included in architecture doc | Submission -> parsing -> storage -> display flow |
| Ingestion Guide | `docs/ingestion-guide.md` | How to configure rsync scripts to submit logs |
| Troubleshooting | `docs/troubleshooting.md` | Common issues and solutions |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Documentation references outdated code | Docs should be updated alongside code changes via PR checklist |
| Environment variable added without docs | CI check or PR template reminder to update env var reference |
| Architecture changes | Architecture doc updated in the same PR as the change |

## 8. Dependencies

- None (documentation can be written against current codebase)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-22 | 0.1.0 | finish06 | Initial spec from TODO conversion |
