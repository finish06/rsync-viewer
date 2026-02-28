# Feature Specification: Structured Logging

**Version:** 0.1.0
**Status:** Complete
**Created:** 2026-02-19
**Milestone:** M1 — Foundation

## Feature Description

Add structured JSON logging with request/response tracking, correlation IDs, and configurable log levels. Replace any print statements or ad-hoc logging with a centralized logging system that outputs machine-parseable JSON logs suitable for homelab log aggregation (e.g., Loki, journald).

## User Story

As a **homelab administrator**, I want **structured, machine-readable logs** so that **I can monitor API activity, debug issues, and integrate with my log aggregation stack**.

## Acceptance Criteria

### Logging Infrastructure

- **AC-001:** Application uses Python's `logging` module with a JSON formatter that outputs one JSON object per log line.
- **AC-002:** Each log entry includes at minimum: `timestamp` (ISO 8601), `level` (INFO/WARNING/ERROR), `message`, `logger` (module name).
- **AC-003:** Log level is configurable via the `LOG_LEVEL` environment variable (default: `INFO`).

### Request/Response Logging

- **AC-004:** Every HTTP request logs: method, path, status code, duration (ms), and client IP.
- **AC-005:** A unique `request_id` (UUID4) is generated per request and included in all log entries for that request.
- **AC-006:** The `request_id` is returned in the `X-Request-ID` response header.
- **AC-007:** Request logging does not log sensitive data (API key values, request bodies containing credentials).

### Domain Event Logging

- **AC-008:** Sync log creation logs: source name, parsed field count, file count, and whether it was a dry run (at INFO level).
- **AC-009:** API key authentication failures log: the attempted endpoint and client IP (at WARNING level). API key values are never logged.
- **AC-010:** Parser failures (fields that couldn't be parsed) log: which fields were None after parsing (at WARNING level).

### Configuration

- **AC-011:** Uvicorn access logs are suppressed or unified with the application logger to avoid duplicate request logging.
- **AC-012:** A `LOG_FORMAT` environment variable allows switching between `json` (default) and `text` (human-readable for local development).

## User Test Cases

### TC-001: Request logs include required fields
**Precondition:** Application running with LOG_LEVEL=INFO
**Steps:**
1. Send GET request to `/health`
2. Inspect application log output
**Expected:** JSON log line with `timestamp`, `level`, `message`, `request_id`, `method: "GET"`, `path: "/health"`, `status_code: 200`, `duration_ms`
**Maps to:** AC-001, AC-002, AC-004, AC-005

### TC-002: Request ID returned in response header
**Precondition:** None
**Steps:**
1. Send any HTTP request
2. Inspect response headers
**Expected:** `X-Request-ID` header present with a valid UUID4 value
**Maps to:** AC-006

### TC-003: Sync log creation produces domain log
**Precondition:** Valid API key
**Steps:**
1. POST a sync log with raw rsync content
2. Inspect log output
**Expected:** INFO log with source_name, file_count, is_dry_run
**Maps to:** AC-008

### TC-004: API key failure logged without key value
**Precondition:** None
**Steps:**
1. Send request with invalid API key
2. Inspect log output
**Expected:** WARNING log mentioning the endpoint and client IP, but NOT the API key value
**Maps to:** AC-009, AC-007

### TC-005: Log level is configurable
**Precondition:** LOG_LEVEL=WARNING
**Steps:**
1. Send a successful GET request
2. Inspect log output
**Expected:** No INFO-level request log appears (suppressed by WARNING threshold)
**Maps to:** AC-003

## Data Model

No database changes. New configuration fields:

| Setting | Type | Default | Source |
|---------|------|---------|--------|
| LOG_LEVEL | str | "INFO" | Environment variable |
| LOG_FORMAT | str | "json" | Environment variable |

## API Contract

No new endpoints. Changes:

- All responses include `X-Request-ID` header (UUID4)
- No changes to request/response body schemas

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| LOG_LEVEL set to invalid value | Default to INFO, log a warning about invalid config |
| Very long request body | Do not log full body; log content-length only |
| Health check endpoint | Log at DEBUG level (not INFO) to reduce noise |
| Static file requests | Do not log (or log at DEBUG level) |
| Concurrent requests | Each gets unique request_id, logs don't interleave |

## Implementation Notes

- Use `python-json-logger` or a custom `logging.Formatter` for JSON output
- Implement request tracking as FastAPI middleware
- Store `request_id` in a context variable (`contextvars`) for access across the call stack
- Consider adding `request_id` to error responses (ties into error-handling spec)

## Screenshot Checkpoints

N/A — Infrastructure change, no UI modifications.
