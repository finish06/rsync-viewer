# Implementation Plan: Changelog Viewer

**Spec Version:** 0.1.0
**Created:** 2026-02-24
**Spec:** specs/changelog-viewer.md
**Team Size:** Solo
**Estimated Duration:** ~4 hours

## Overview

Add a "Changelog" tab to the settings page that parses `CHANGELOG.md` at runtime and renders version history as HTMX-powered accordions. No database changes needed.

## Acceptance Criteria Analysis

### AC-001: Changelog tab on settings page (Must)
- **Complexity:** Simple
- **Tasks:** Add tab to settings.html, conditionally render based on changelog availability
- **Dependencies:** AC-006 (hide logic), changelog parser

### AC-002: Version accordion headers with version + date (Must)
- **Complexity:** Simple
- **Tasks:** HTML partial template with version headers, parse version/date from CHANGELOG.md
- **Dependencies:** Changelog parser

### AC-003: HTMX expand/collapse (Must)
- **Complexity:** Simple
- **Tasks:** HTMX hx-get on version headers, route returning version detail partial
- **Dependencies:** AC-002

### AC-004: Grouped change sections (Must)
- **Complexity:** Medium
- **Tasks:** Parse Added/Fixed/Changed/Documentation sections, render grouped in partial
- **Dependencies:** Changelog parser, AC-003

### AC-005: "Current" badge (Must)
- **Complexity:** Simple
- **Tasks:** Compare parsed version to app version, add badge in template
- **Dependencies:** App version constant in config, AC-002

### AC-006: Hide tab when file missing (Must)
- **Complexity:** Simple
- **Tasks:** Check file existence in settings route, conditionally include tab
- **Dependencies:** None

### AC-007: Unreleased section (Should)
- **Complexity:** Simple
- **Tasks:** Parser handles `## [Unreleased]` header, renders at top
- **Dependencies:** Changelog parser

### AC-008: All Keep a Changelog section types (Should)
- **Complexity:** Simple
- **Tasks:** Parser handles: Added, Changed, Deprecated, Removed, Fixed, Security, Documentation
- **Dependencies:** Changelog parser

## Implementation Phases

### Phase 1: RED — Write failing tests (~1.5 hours)

| Task ID | Description | AC | Effort |
|---------|-------------|-----|--------|
| TASK-001 | Write changelog parser tests: parse valid CHANGELOG.md, extract versions, dates, sections | AC-002, AC-004, AC-007, AC-008 | 30min |
| TASK-002 | Write changelog parser edge case tests: missing file, empty file, malformed content | AC-006 | 15min |
| TASK-003 | Write settings page tests: changelog tab visible when file exists, hidden when missing | AC-001, AC-006 | 15min |
| TASK-004 | Write HTMX endpoint tests: GET changelog list, GET version detail, 404 for unknown version | AC-003, AC-004 | 20min |
| TASK-005 | Write "Current" badge test: version matching app version gets badge | AC-005 | 10min |

**Phase output:** `tests/test_changelog.py` with ~15-18 failing tests

### Phase 2: GREEN — Implement to pass tests (~2 hours)

| Task ID | Description | AC | Effort | Dependencies |
|---------|-------------|-----|--------|--------------|
| TASK-006 | Create `app/services/changelog_parser.py` with `parse_changelog(path) -> list[ChangelogVersion]` | AC-002, AC-004, AC-007, AC-008 | 30min | — |
| TASK-007 | Add `app_version` setting to `app/config.py` (read from a constant or env var) | AC-005 | 5min | — |
| TASK-008 | Create `app/schemas/changelog.py` with `ChangelogVersion` Pydantic model | AC-004 | 10min | — |
| TASK-009 | Add changelog tab to `app/templates/settings.html` (conditionally shown) | AC-001, AC-006 | 15min | TASK-006 |
| TASK-010 | Create `app/templates/partials/changelog_list.html` — version accordion headers | AC-002, AC-005, AC-007 | 15min | TASK-008 |
| TASK-011 | Create `app/templates/partials/changelog_detail.html` — expanded version content | AC-004 | 15min | TASK-008 |
| TASK-012 | Add HTMX routes in `app/main.py`: GET `/htmx/changelog`, GET `/htmx/changelog/{version}` | AC-003, AC-004 | 20min | TASK-006, TASK-009 |
| TASK-013 | Update settings route to pass `changelog_available` flag to template | AC-001, AC-006 | 10min | TASK-006 |

### Phase 3: REFACTOR + VERIFY (~30 min)

| Task ID | Description | Effort |
|---------|-------------|--------|
| TASK-014 | Run full test suite, verify no regressions | 10min |
| TASK-015 | Run ruff check + ruff format | 5min |
| TASK-016 | Run mypy | 5min |
| TASK-017 | Review code for cleanup opportunities | 10min |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/changelog_parser.py` | Create | Parse CHANGELOG.md into structured data |
| `app/schemas/changelog.py` | Create | ChangelogVersion Pydantic model |
| `app/config.py` | Modify | Add `app_version` setting |
| `app/main.py` | Modify | Add 2 HTMX routes, update settings route |
| `app/templates/settings.html` | Modify | Add changelog tab with conditional display |
| `app/templates/partials/changelog_list.html` | Create | Version accordion list partial |
| `app/templates/partials/changelog_detail.html` | Create | Version detail partial |
| `tests/test_changelog.py` | Create | All changelog tests (~15-18 tests) |

## Key Design Decisions

1. **No database** — CHANGELOG.md is parsed at request time. The file is small (<200 lines) so no caching needed initially.
2. **Two HTMX routes** — `/htmx/changelog` returns the full version list (tab content), `/htmx/changelog/{version}` returns a single version's expanded detail.
3. **App version** — Add `app_version: str = "1.7.0"` to Settings. Update this when releasing. Used for "Current" badge matching.
4. **Settings page layout** — The existing settings page uses sections (Appearance, Webhooks). The changelog will be a new section at the bottom, or tabs if we add tab navigation. Since the spec says "tab", we'll add a simple tab bar to the settings page (Webhooks | Changelog).
5. **Accordion pattern** — Same HTMX pattern as webhooks list: header with `hx-get` that swaps content into a target div. Toggle by checking if content div is already populated.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CHANGELOG.md format varies between releases | Low | Low | Parser handles missing sections gracefully |
| Settings page layout breaks with new tab | Low | Medium | Test existing settings functionality after changes |
| App version gets out of sync | Medium | Low | Could read from a `__version__` constant instead of config |

## Testing Strategy

- **Unit tests:** Changelog parser (parse valid/invalid/edge cases)
- **Integration tests:** HTMX endpoints return correct HTML partials
- **Settings page tests:** Tab visibility, conditional rendering
- **Coverage target:** All 8 ACs covered with at least 1 test each

## Effort Summary

| Phase | Estimated |
|-------|-----------|
| Phase 1: RED (tests) | 1.5 hours |
| Phase 2: GREEN (implementation) | 2 hours |
| Phase 3: REFACTOR + VERIFY | 0.5 hours |
| **Total** | **~4 hours** |

## Next Steps

1. Approve this plan
2. Run `/add:tdd-cycle specs/changelog-viewer.md` to execute
