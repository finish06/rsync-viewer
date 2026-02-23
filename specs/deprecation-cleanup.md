# Spec: Deprecation Cleanup

**Version:** 0.1.0
**Created:** 2026-02-23
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Replace all uses of the deprecated `datetime.utcnow()` with the timezone-aware `datetime.now(datetime.UTC)` across the entire codebase — application code, models, and tests. Audit for any other Python deprecation warnings and fix them.

### User Story

As a developer working on rsync-viewer, I want the codebase to be free of deprecation warnings, so that test output is clean, the code is forward-compatible with future Python versions, and we follow modern best practices.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | All `datetime.utcnow()` calls in application code (`app/`) are replaced with `datetime.now(datetime.UTC)` | Must |
| AC-002 | All `datetime.utcnow()` calls in test code (`tests/`) are replaced with `datetime.now(datetime.UTC)` | Must |
| AC-003 | All model `default_factory=datetime.utcnow` fields are replaced with a timezone-aware factory | Must |
| AC-004 | Running `pytest` produces zero `DeprecationWarning` lines related to `datetime.utcnow()` | Must |
| AC-005 | No other Python deprecation warnings remain in the test output | Should |
| AC-006 | All existing tests continue to pass after the migration (no regressions) | Must |
| AC-007 | `ruff check .` passes cleanly | Must |
| AC-008 | `mypy app/` passes cleanly | Must |
| AC-009 | Database behavior is unchanged — PostgreSQL `timestamp without time zone` columns strip tzinfo on insert, so no schema migration is needed | Must |

## 3. User Test Cases

### TC-001: Clean test output

**Precondition:** All changes applied
**Steps:**
1. Run `pytest tests/ -v`
2. Search output for "DeprecationWarning" or "datetime.utcnow"
**Expected Result:** Zero deprecation warnings related to datetime. All tests pass.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-004, AC-005, AC-006

### TC-002: Application code audit

**Precondition:** All changes applied
**Steps:**
1. Run `grep -r "datetime.utcnow" app/`
2. Run `grep -r "datetime.utcnow" tests/`
**Expected Result:** Zero matches in both directories.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-001, AC-002, AC-003

### TC-003: Quality gates pass

**Precondition:** All changes applied
**Steps:**
1. Run `ruff check .`
2. Run `mypy app/`
**Expected Result:** Both pass with zero errors.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-007, AC-008

## 4. Data Model

No schema changes. PostgreSQL `timestamp without time zone` columns automatically strip timezone info on insert, so passing `datetime.now(datetime.UTC)` (which is tz-aware) works identically to `datetime.utcnow()` (which is naive).

### Model Default Factory Change

All models with `default_factory=datetime.utcnow` will be updated to use a shared helper:

```python
from datetime import datetime, UTC

def utc_now() -> datetime:
    return datetime.now(UTC)
```

This avoids repeating `lambda: datetime.now(UTC)` on every field.

## 5. Scope of Changes

### Application Code (app/)

| File | Occurrences | Change |
|------|-------------|--------|
| `app/api/deps.py` | 2 | Replace `datetime.utcnow()` calls |
| `app/api/endpoints/monitors.py` | 1 | Replace `datetime.utcnow()` |
| `app/api/endpoints/webhooks.py` | 2 | Replace `datetime.utcnow()` |
| `app/errors.py` | 1 | Replace `datetime.utcnow()` |
| `app/main.py` | 3 | Replace `datetime.utcnow()` |
| `app/services/stale_checker.py` | 1 | Replace `datetime.utcnow()` |
| `app/models/sync_log.py` | 2 | Replace `default_factory` |
| `app/models/failure_event.py` | 2 | Replace `default_factory` |
| `app/models/monitor.py` | 2 | Replace `default_factory` |
| `app/models/webhook.py` | 2 | Replace `default_factory` |
| `app/models/webhook_options.py` | 2 | Replace `default_factory` |
| `app/models/notification_log.py` | 1 | Replace `default_factory` |

### Test Code (tests/)

| File | Occurrences |
|------|-------------|
| `tests/conftest.py` | 2 |
| `tests/test_api.py` | 2 |
| `tests/test_api_key_debounce.py` | 7 |
| `tests/test_average_transfer_rate.py` | 4 |
| `tests/test_date_range_quick_select.py` | 6 |
| `tests/test_error_handling.py` | 1 |
| `tests/test_htmx.py` | 8 |
| `tests/test_notification_history.py` | 6 |
| `tests/test_security_hardening.py` | 2 |
| `tests/unit/test_failures_api.py` | 4 |
| `tests/unit/test_stale_checker.py` | 7 |

**Total: ~61 replacements across 23 files.**

## 6. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| `datetime.now(UTC)` passed to PostgreSQL `timestamp without time zone` column | PostgreSQL strips the tz info — stored value is identical to `datetime.utcnow()` |
| Comparison between old naive datetimes (from DB) and new tz-aware datetimes | Not an issue — SQLModel/SQLAlchemy returns naive datetimes from `timestamp without time zone` columns, and comparisons happen at the DB level |
| `default_factory` with `utc_now` helper | Works identically to previous `datetime.utcnow` — called at row creation time |

## 7. Dependencies

- Python 3.11+ (for `datetime.UTC` constant — already satisfied by project requirement)
- No new library dependencies

## 8. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-23 | 0.1.0 | finish06 | Initial spec |
