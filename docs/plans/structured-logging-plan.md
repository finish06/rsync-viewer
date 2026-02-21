# Implementation Plan: Structured Logging

**Spec:** specs/structured-logging.md v0.1.0
**Created:** 2026-02-19
**Team Size:** Solo
**Estimated Duration:** 2-3 hours

## Overview

Add structured JSON logging with request/response tracking, correlation IDs, and configurable log levels to the FastAPI application.

## Implementation Phases

### Phase 1: Logging Configuration (20min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-001 | Add `LOG_LEVEL` and `LOG_FORMAT` to `app/config.py` Settings class | 5min | AC-003, AC-012 |
| TASK-002 | Create `app/logging_config.py` with JSON formatter and logging setup function | 15min | AC-001, AC-002, AC-003, AC-012 |

**Files created:** `app/logging_config.py`
**Files modified:** `app/config.py`

### Phase 2: Request Middleware (30min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-003 | Create request logging middleware in `app/middleware.py` — generate request_id (UUID4), store in contextvars, log request/response with duration | 20min | AC-004, AC-005, AC-006, AC-007 |
| TASK-004 | Register middleware in `app/main.py` and add `X-Request-ID` response header | 10min | AC-006 |

**Files created:** `app/middleware.py`
**Files modified:** `app/main.py`

### Phase 3: Domain Event Logging (20min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-005 | Add sync log creation logging in `app/api/endpoints/sync_logs.py` — log source_name, file_count, is_dry_run | 10min | AC-008 |
| TASK-006 | Add auth failure logging in `app/api/deps.py` — log endpoint and client IP, never log key values | 5min | AC-009, AC-007 |
| TASK-007 | Add parser warning logging in `app/services/rsync_parser.py` — log when fields are None after parsing | 5min | AC-010 |

**Files modified:** `app/api/endpoints/sync_logs.py`, `app/api/deps.py`, `app/services/rsync_parser.py`

### Phase 4: Uvicorn Integration (10min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-008 | Configure uvicorn to suppress default access logs (handled by middleware) | 10min | AC-011 |

**Files modified:** `app/main.py` or uvicorn config

### Phase 5: Add python-json-logger Dependency (5min)

| Task ID | Description | Effort | AC Coverage |
|---------|-------------|--------|-------------|
| TASK-009 | Add `python-json-logger` to `requirements.txt` and `requirements-dev.txt` | 5min | AC-001 |

**Files modified:** `requirements.txt`, `requirements-dev.txt`

## Spec Traceability

| Task | Acceptance Criteria |
|------|-------------------|
| TASK-001 | AC-003, AC-012 |
| TASK-002 | AC-001, AC-002, AC-003, AC-012 |
| TASK-003 | AC-004, AC-005, AC-006, AC-007 |
| TASK-004 | AC-006 |
| TASK-005 | AC-008 |
| TASK-006 | AC-009, AC-007 |
| TASK-007 | AC-010 |
| TASK-008 | AC-011 |
| TASK-009 | AC-001 |

## Notes

- Use `contextvars.ContextVar` for request_id to make it available across the call stack without threading issues
- Health check and static file requests should log at DEBUG level to reduce noise
- The logging setup should be called once in the lifespan handler, not on import
- JSON formatter: use `python-json-logger` library for reliable JSON output
- Consider: request_id from this spec can feed into error-handling spec's error responses
