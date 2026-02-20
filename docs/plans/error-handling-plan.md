# Implementation Plan: Comprehensive Error Handling

**Spec:** specs/error-handling.md v0.1.0
**Created:** 2026-02-19
**Team Size:** Solo
**Estimated Duration:** 2-3 hours

## Overview

Add consistent structured error responses, global exception handling middleware, and protected database/input operations across the FastAPI application.

## Implementation Phases

### Phase 1: Error Response Schema & Error Codes (20min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-001 | Update `ErrorResponse` in `app/schemas/sync_log.py` with `error_code`, `message`, `detail`, `timestamp`, `path`, `validation_errors` fields | 10min | AC-001, AC-002, AC-010 |
| TASK-002 | Create error code constants in `app/errors.py` (registry of error codes) | 10min | AC-003, AC-008 |

**Files created:** `app/errors.py`
**Files modified:** `app/schemas/sync_log.py`

### Phase 2: Global Exception Handlers (30min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-003 | Add global `Exception` handler in `app/main.py` that returns structured 500 responses (no stack traces) | 15min | AC-004 |
| TASK-004 | Add `RequestValidationError` handler to wrap Pydantic validation errors in structured format with `validation_errors` array | 15min | AC-002 |

**Files modified:** `app/main.py`

### Phase 3: Endpoint Error Handling (30min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-005 | Update `app/api/deps.py` — replace HTTPExceptions with structured error responses using error codes | 10min | AC-001, AC-003 |
| TASK-006 | Update `app/api/endpoints/sync_logs.py` — wrap database commits in try/except, use structured errors for 404 | 10min | AC-005 |
| TASK-007 | Update HTMX endpoints in `app/main.py` — wrap `datetime.fromisoformat()` calls in try/except, return 400 | 10min | AC-006 |

**Files modified:** `app/api/deps.py`, `app/api/endpoints/sync_logs.py`, `app/main.py`

### Phase 4: Parser Safety (10min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-008 | Add try/except in `RsyncParser._parse_number()` to handle non-numeric input gracefully | 10min | AC-007 |

**Files modified:** `app/services/rsync_parser.py`

### Phase 5: OpenAPI Documentation (10min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-009 | Update endpoint response models to use the new `ErrorResponse` schema with examples showing error codes | 10min | AC-009 |

**Files modified:** `app/api/endpoints/sync_logs.py`

## Spec Traceability

| Task | Acceptance Criteria |
|------|-------------------|
| TASK-001 | AC-001, AC-002, AC-010 |
| TASK-002 | AC-003, AC-008 |
| TASK-003 | AC-004 |
| TASK-004 | AC-002 |
| TASK-005 | AC-001, AC-003 |
| TASK-006 | AC-005 |
| TASK-007 | AC-006 |
| TASK-008 | AC-007 |
| TASK-009 | AC-009 |

## Notes

- ErrorResponse must keep `detail` field for backward compatibility (AC-010)
- HTMX endpoints return HTML, so error handling there returns template responses, not JSON
- The error handling spec pairs with structured-logging spec — request_id from logging can be added to error responses later
