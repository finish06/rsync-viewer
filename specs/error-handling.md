# Feature Specification: Comprehensive Error Handling

**Version:** 0.1.0
**Status:** Approved
**Created:** 2026-02-19
**Milestone:** M1 — Foundation

## Feature Description

Add consistent, structured error handling across the application. Replace ad-hoc HTTPExceptions with a unified error response format, add exception middleware for unhandled errors, protect database operations and input parsing with try/except blocks, and define application error codes.

## User Story

As a **homelab administrator integrating rsync scripts with the API**, I want **consistent, descriptive error responses** so that **I can programmatically detect and handle failures in my automation scripts**.

## Acceptance Criteria

### Error Response Format

- **AC-001:** All API error responses (4xx and 5xx) return a consistent JSON structure with fields: `error_code` (string), `message` (string), `detail` (string or null), `timestamp` (ISO 8601), and `path` (string).
- **AC-002:** Validation errors (422) include a `validation_errors` array with field-level error details in addition to the standard error fields.
- **AC-003:** The `error_code` field uses uppercase snake_case identifiers (e.g., `RESOURCE_NOT_FOUND`, `VALIDATION_ERROR`, `API_KEY_REQUIRED`).

### Exception Handling

- **AC-004:** A global exception handler catches all unhandled exceptions and returns a 500 response using the standard error format (no stack traces leaked to the client).
- **AC-005:** Database commit failures (`IntegrityError`, `OperationalError`) are caught and return appropriate error responses (409 for conflicts, 503 for connection issues).
- **AC-006:** Invalid date query parameters in HTMX endpoints return 400 Bad Request instead of 500 Internal Server Error.
- **AC-007:** The rsync parser's `_parse_number()` method handles non-numeric input without raising unhandled exceptions.

### Error Codes

- **AC-008:** An error code registry is defined with at least these codes: `API_KEY_REQUIRED`, `API_KEY_INVALID`, `RESOURCE_NOT_FOUND`, `VALIDATION_ERROR`, `DATABASE_ERROR`, `INTERNAL_ERROR`, `BAD_REQUEST`.
- **AC-009:** Error codes are documented in the OpenAPI schema via response model examples.

### Backward Compatibility

- **AC-010:** The `detail` field remains present in error responses to maintain compatibility with existing clients that parse FastAPI's default error format.

## User Test Cases

### TC-001: API returns structured error for missing API key
**Precondition:** No API key header sent
**Steps:**
1. POST to `/api/v1/sync-logs` without `X-API-Key` header
2. Inspect response body
**Expected:** 401 status, body contains `error_code: "API_KEY_REQUIRED"`, `message`, `timestamp`, `path`
**Maps to:** AC-001, AC-003, AC-008

### TC-002: API returns structured error for not found
**Precondition:** No sync log with given ID exists
**Steps:**
1. GET `/api/v1/sync-logs/00000000-0000-0000-0000-000000000000`
2. Inspect response body
**Expected:** 404 status, body contains `error_code: "RESOURCE_NOT_FOUND"`
**Maps to:** AC-001, AC-003, AC-008

### TC-003: Validation error includes field details
**Precondition:** None
**Steps:**
1. POST to `/api/v1/sync-logs` with `X-API-Key` header but empty JSON body `{}`
2. Inspect response body
**Expected:** 422 status, body contains `error_code: "VALIDATION_ERROR"`, `validation_errors` array with field names
**Maps to:** AC-002, AC-003

### TC-004: Invalid date parameter returns 400
**Precondition:** None
**Steps:**
1. GET `/htmx/sync-table?start_date=not-a-date`
2. Inspect response
**Expected:** 400 status (not 500), body or page indicates bad request
**Maps to:** AC-006

### TC-005: Unhandled exception returns structured 500
**Precondition:** An unexpected error occurs (simulated in test)
**Steps:**
1. Trigger an unhandled exception in an endpoint
2. Inspect response body
**Expected:** 500 status, body contains `error_code: "INTERNAL_ERROR"`, no stack trace
**Maps to:** AC-004

## Data Model

### ErrorResponse (updated schema)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| error_code | str | Yes | Uppercase snake_case error identifier |
| message | str | Yes | Human-readable error description |
| detail | str/null | Yes | Additional detail (backward compat with FastAPI) |
| timestamp | datetime | Yes | ISO 8601 when error occurred |
| path | str | Yes | Request path that triggered the error |
| validation_errors | list[dict]/null | No | Field-level validation errors (422 only) |

## API Contract

No new endpoints. Changes affect error responses on existing endpoints:

- All 4xx/5xx responses conform to the updated `ErrorResponse` schema
- OpenAPI docs updated with error response examples

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Database connection lost mid-request | 503 with `DATABASE_ERROR` code |
| Malformed UUID in path parameter | 422 with `VALIDATION_ERROR` (FastAPI handles) |
| Request body exceeds size limit | 413 or FastAPI default, wrapped in standard format |
| Concurrent duplicate submissions | 409 with `DATABASE_ERROR` if constraint violation |
| Parser receives binary garbage | Returns ParsedRsyncOutput with None fields (existing behavior, no crash) |

## Screenshot Checkpoints

N/A — API-only changes, no UI modifications.
