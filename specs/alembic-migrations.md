# Spec: Alembic Database Migrations

**Version:** 0.1.0
**Created:** 2026-03-01
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Replace `SQLModel.metadata.create_all()` with Alembic for database schema management. Migrations run automatically on app startup (`alembic upgrade head`), enabling safe, versioned schema changes for production Postgres without manual ALTER TABLE commands. A baseline migration captures the current schema. Autogenerate is the standard workflow for creating new migrations.

### User Story

As a developer, I want database schema changes managed through versioned migration files, so that I can safely evolve the schema across development and production environments without manual SQL.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Alembic is initialized with `alembic.ini` and `alembic/` directory in the project root | Must |
| AC-002 | `alembic/env.py` is configured to use SQLModel metadata and reads `DATABASE_URL` from app config | Must |
| AC-003 | A baseline migration exists that represents the full current schema (all existing tables, columns, indexes, constraints) | Must |
| AC-004 | App startup runs `alembic upgrade head` instead of `SQLModel.metadata.create_all()` | Must |
| AC-005 | A fresh database (empty) can be fully created by running `alembic upgrade head` | Must |
| AC-006 | An existing production database can be stamped at the baseline without re-running the initial migration (`alembic stamp head`) | Must |
| AC-007 | `alembic revision --autogenerate -m "description"` correctly detects model changes and generates migration files | Must |
| AC-008 | Migration files are committed to git and included in the Docker image | Must |
| AC-009 | The test suite continues to use `create_all()` with in-memory SQLite (not affected by Alembic) | Must |
| AC-010 | `entrypoint.sh` runs migrations before starting uvicorn (Docker deployment) | Must |
| AC-011 | The README Development section documents the migration workflow for developers | Should |
| AC-012 | Downgrade is supported for at least the most recent migration (`alembic downgrade -1`) | Should |

## 3. User Test Cases

### TC-001: Fresh database setup via migrations

**Precondition:** Empty Postgres database, app not yet started
**Steps:**
1. Start the app (or run `alembic upgrade head` manually)
2. Connect to the database and inspect tables
**Expected Result:** All tables exist with correct columns, indexes, and constraints matching the current SQLModel definitions
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-002: Existing production database stamped at baseline

**Precondition:** Production Postgres with existing schema (created by `create_all()`)
**Steps:**
1. Run `alembic stamp head` against the production database
2. Run `alembic current` to verify
**Expected Result:** Alembic reports the database is at the head revision. No tables were altered. `alembic_version` table exists with the baseline revision ID.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-003: Developer adds a new model field

**Precondition:** Alembic initialized, baseline migration applied
**Steps:**
1. Add a new field to a model (e.g., `preferences` JSON column on User)
2. Run `alembic revision --autogenerate -m "add user preferences"`
3. Review the generated migration file
4. Run `alembic upgrade head`
**Expected Result:** Migration file correctly contains `op.add_column(...)`. After upgrade, the column exists in the database.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-004: App starts and auto-migrates

**Precondition:** Docker Compose environment, database at previous migration
**Steps:**
1. Deploy a new app version with a new migration file
2. `docker-compose up -d`
**Expected Result:** App starts, runs `alembic upgrade head`, then serves requests. No manual intervention.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-005: Tests unaffected

**Precondition:** Test suite with in-memory SQLite
**Steps:**
1. Run `pytest`
**Expected Result:** All existing tests pass. Tests continue to use `create_all()`. No Alembic dependency in test fixtures.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

## 4. Data Model

### alembic_version (auto-created by Alembic)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version_num | VARCHAR(32) | Yes | Current migration revision ID |

No other data model changes. This spec is infrastructure — it manages how model changes are applied, not what the models contain.

## 5. API Contract (if applicable)

N/A — no API endpoints. This is infrastructure tooling.

## 6. UI Behavior (if applicable)

N/A — no UI changes.

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| `alembic upgrade head` on already-current database | No-op, app starts normally |
| Database is unreachable at startup | Migration fails, app fails to start (existing behavior with `create_all()`) |
| Migration file conflicts (two devs add migrations simultaneously) | Alembic detects branch and errors. Developer resolves by creating a merge migration (`alembic merge heads`). |
| Downgrade attempted past baseline | Alembic errors cleanly (baseline has no downgrade to empty) |
| SQLite in dev (no Postgres) | Alembic works with SQLite for local dev. Autogenerate may miss some Postgres-specific features (e.g., JSONB vs JSON). |

## 8. Dependencies

- `alembic>=1.13.0` (already in `requirements.txt`)
- `SQLModel` metadata (already defined in models)
- `DATABASE_URL` from `app.config` (already exists)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-01 | 0.1.0 | Claude | Initial spec from /add:spec interview |
