# Spec: Version Endpoint

**Version:** 0.1.0
**Created:** 2026-03-15
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Add a `GET /version` endpoint that returns build and runtime metadata as JSON, and export the same information as Prometheus metrics. Currently, the service stores `app_version` via the `APP_VERSION` env var and exposes it only through the Prometheus `app_info` gauge and the OpenAPI schema. Operators need a single endpoint to verify what build is running, when it started, how long it has been up, and what Python version is running it — all without parsing Prometheus output or checking the OpenAPI docs. Additionally, a `rsync_viewer_build_info` Prometheus gauge enables Grafana annotations on version changes.

### User Story

As an **operator**, I want a dedicated `/version` endpoint that shows build metadata, runtime info, and uptime, so that I can verify deployments at a glance and track version changes in Grafana via Prometheus metrics.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | `GET /version` returns HTTP 200 with a JSON body containing: `version`, `python_version`, `os`, `arch`, `hostname`, `uptime_seconds`, `start_time` | Must |
| AC-002 | `version` is populated from `settings.app_version` (set via `APP_VERSION` env var, default `"dev"`) | Must |
| AC-003 | `python_version` is populated from `platform.python_version()` at runtime | Must |
| AC-004 | `os` and `arch` are populated from `platform.system()` and `platform.machine()` | Must |
| AC-005 | `hostname` is populated from `socket.gethostname()` at startup | Must |
| AC-006 | `start_time` is an ISO 8601 UTC timestamp recorded at application startup. `uptime_seconds` is calculated as seconds since `start_time` at request time. | Must |
| AC-007 | A Prometheus gauge `rsync_viewer_build_info` with value 1 and labels `version`, `python_version` is registered and exported on `/metrics` | Must |
| AC-008 | `/version` is unauthenticated (public, like `/health` and `/metrics`) | Must |
| AC-009 | `/version` is exempt from rate limiting (registered in `PUBLIC_PATHS`) | Must |
| AC-010 | The `/health` response also includes a `version` field | Should |
| AC-011 | All existing tests pass without modification | Must |
| AC-012 | The `/version` response has `Content-Type: application/json` (FastAPI default) | Must |

## 3. User Test Cases

### TC-001: Version endpoint returns all fields

**Precondition:** Service is running with `APP_VERSION=v2.3.1`
**Steps:**
1. Send `GET /version`
**Expected Result:** HTTP 200 with JSON body:
```json
{
  "version": "v2.3.1",
  "python_version": "3.11.11",
  "os": "Linux",
  "arch": "aarch64",
  "hostname": "rsync-viewer-app",
  "uptime_seconds": 3621.5,
  "start_time": "2026-03-15T12:00:00Z"
}
```
**Maps to:** AC-001, AC-002, AC-003, AC-004, AC-005, AC-006

### TC-002: Prometheus build_info metric exported

**Precondition:** Service is running
**Steps:**
1. Send `GET /metrics`
2. Search for `rsync_viewer_build_info`
**Expected Result:** Output contains:
```
rsync_viewer_build_info{version="v2.3.1",python_version="3.11.11"} 1.0
```
**Maps to:** AC-007

### TC-003: Uptime seconds increases over time

**Precondition:** Service has been running for at least a few seconds
**Steps:**
1. Send `GET /version`, note `uptime_seconds`
2. Wait 2 seconds
3. Send `GET /version` again, note `uptime_seconds`
**Expected Result:** Second `uptime_seconds` is approximately 2 greater than the first.
**Maps to:** AC-006

### TC-004: Dev build shows default version

**Precondition:** Service is running without `APP_VERSION` set
**Steps:**
1. Send `GET /version`
**Expected Result:** `version: "dev"`. Runtime fields (`python_version`, `hostname`, etc.) are still populated.
**Maps to:** AC-001, AC-002

### TC-005: Endpoint is unauthenticated

**Precondition:** Service is running
**Steps:**
1. Send `GET /version` without any API key or JWT
**Expected Result:** HTTP 200 (not 401 or 302 redirect)
**Maps to:** AC-008

## 4. Data Model

No database changes. New response schema only.

### Response Schema: `VersionInfo`

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `version` | string | `settings.app_version` | Build version from `APP_VERSION` env |
| `python_version` | string | `platform.python_version()` | Python runtime version |
| `os` | string | `platform.system()` | Operating system name |
| `arch` | string | `platform.machine()` | CPU architecture |
| `hostname` | string | `socket.gethostname()` | Container/host hostname |
| `uptime_seconds` | float | `time.monotonic() - start_time` | Seconds since startup |
| `start_time` | string | ISO 8601 UTC, recorded at startup | When the process started |

### New Prometheus Metric

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rsync_viewer_build_info` | Gauge (value=1) | `version`, `python_version` | Build identity for Grafana annotations |

## 5. API Contract

### `GET /version`

**Description:** Returns build and runtime metadata.

**Response (200):**
```json
{
  "version": "v2.3.1",
  "python_version": "3.11.11",
  "os": "Linux",
  "arch": "aarch64",
  "hostname": "rsync-viewer-app",
  "uptime_seconds": 86421.3,
  "start_time": "2026-03-15T12:00:00Z"
}
```

## 6. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| `APP_VERSION` not set | `version: "dev"` (config default) |
| `socket.gethostname()` fails | Set `hostname` to `"unknown"` |
| Extremely long uptime (months) | `uptime_seconds` is float — handles large values |
| Container hostname changes at runtime | `hostname` captured once at startup |

## 7. Dependencies

- `app/main.py` — add `/version` endpoint, record `start_time` in lifespan
- `app/metrics.py` — add `rsync_viewer_build_info` gauge
- `app/middleware.py` — add `/version` to `PUBLIC_PATHS`

## 8. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-15 | 0.1.0 | finish06 | Initial spec adapted from cash-drugs version-endpoint |
