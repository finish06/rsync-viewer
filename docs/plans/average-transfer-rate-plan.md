# Implementation Plan: Average Transfer Rate

**Spec Version:** 0.1.0
**Spec:** specs/average-transfer-rate.md
**Created:** 2026-02-20
**Team Size:** Solo
**Estimated Duration:** 1.5-2 hours

## Overview

Add a `format_rate` Jinja2 template filter that computes bytes_received / duration and displays human-readable transfer rates. Add an "Avg Rate" column to the sync table and an "Avg Rate" field to the detail modal. No database changes.

## Objectives

- Display calculated average transfer rate per sync log
- Handle all edge cases (missing data, dry runs, zero duration)
- Follow existing `format_bytes` / `format_duration` filter pattern

## Success Criteria

- All 10 acceptance criteria implemented and tested
- Existing tests unaffected
- No database schema changes

## Implementation Phases

### Phase 1: Template Filter (30min)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-001 | Create `format_rate` Jinja2 filter in `app/main.py`. Takes `bytes_received` (Optional[int]) and `duration` (timedelta). Returns formatted string like "12.50 MB/s". Returns "-" for None bytes, zero/negative duration, or dry runs. Returns "0.00 B/s" for zero bytes with valid duration. Register on `templates.env.filters`. | 30min | None | AC-002, AC-003, AC-005, AC-006, AC-008, AC-009 |

**Details:**
- Follow the pattern of existing `format_bytes` filter
- Signature: `format_rate(bytes_received: Optional[int], duration_seconds: float) -> str`
- Reuse the unit-scaling logic from `format_bytes` but append "/s"
- The template will compute duration_seconds before calling the filter, OR the filter can accept a timedelta

**Simpler approach:** Make it a filter that takes the sync object directly:
- `format_rate(sync)` — accesses `sync.bytes_received`, `sync.start_time`, `sync.end_time`, `sync.is_dry_run`
- Keeps template usage clean: `{{ sync | format_rate }}`
- Handles all edge cases in one place

### Phase 2: Sync Table Column (15min)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-002 | Add "Avg Rate" column header to `partials/sync_table.html` after "Transferred". Add `{{ sync \| format_rate }}` cell in the table body. | 15min | TASK-001 | AC-001 |

**Files Modified:**
- `app/templates/partials/sync_table.html` — add `<th>Avg Rate</th>` and `<td>{{ sync | format_rate }}</td>`

### Phase 3: Detail Modal (10min)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-003 | Add "Avg Rate" detail-item to `partials/sync_detail.html` in the statistics grid, after the "Speed" field. | 10min | TASK-001 | AC-004 |

**Files Modified:**
- `app/templates/partials/sync_detail.html` — add detail-item block

### Phase 4: Tests (45min)

| Task ID | Description | Effort | Dependencies | AC |
|---------|-------------|--------|--------------|-----|
| TASK-004 | Write unit tests for `format_rate` filter: normal rate, auto-scaling (B/s, KB/s, MB/s, GB/s), None bytes, zero duration, dry run, zero bytes. | 30min | TASK-001 | AC-002, AC-003, AC-005, AC-006, AC-007, AC-008 |
| TASK-005 | Write integration tests: sync table contains "Avg Rate" column, detail modal contains "Avg Rate" field. | 15min | TASK-002, TASK-003 | AC-001, AC-004 |

**Files Created:**
- `tests/test_average_transfer_rate.py`

## Effort Summary

| Phase | Estimated | Tasks |
|-------|-----------|-------|
| Phase 1: Filter | 30min | TASK-001 |
| Phase 2: Table | 15min | TASK-002 |
| Phase 3: Modal | 10min | TASK-003 |
| Phase 4: Tests | 45min | TASK-004, TASK-005 |
| **Total** | **~1.5h** | **5 tasks** |

## Spec Traceability

| Task | Acceptance Criteria |
|------|-------------------|
| TASK-001 | AC-002, AC-003, AC-005, AC-006, AC-007, AC-008, AC-009, AC-010 |
| TASK-002 | AC-001 |
| TASK-003 | AC-004 |
| TASK-004 | AC-002, AC-003, AC-005, AC-006, AC-007, AC-008 |
| TASK-005 | AC-001, AC-004 |

## File Change Summary

| File | Action | Reason |
|------|--------|--------|
| `app/main.py` | Modified | Add `format_rate` filter function + register it |
| `app/templates/partials/sync_table.html` | Modified | Add "Avg Rate" column |
| `app/templates/partials/sync_detail.html` | Modified | Add "Avg Rate" to detail grid |
| `tests/test_average_transfer_rate.py` | Created | Tests for filter and template integration |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Division by zero on zero-duration syncs | Medium | High | Guard in filter, return "-" |
| Existing tests break from new table column | Low | Low | Column is additive only |

## Recommended Execution Order

1. TASK-001 (filter function)
2. TASK-004 (unit tests for filter — can write immediately)
3. TASK-002 (table column)
4. TASK-003 (modal field)
5. TASK-005 (integration tests)

## Plan History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-20 | 1.0.0 | Initial plan from /add:plan |
