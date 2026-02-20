# Implementation Plan: Dark Mode & Theme Settings

**Spec:** specs/dark-mode.md v0.1.0
**Created:** 2026-02-19
**Team Size:** Solo
**Estimated Duration:** 4-6 hours

## Overview

Add a theme system (light/dark/system) to the Rsync Log Viewer dashboard. The existing CSS custom properties architecture makes this straightforward — define dark overrides via `[data-theme="dark"]`, add a settings page with a theme toggle, and wire up JavaScript for localStorage persistence and OS preference detection.

## Acceptance Criteria Analysis

### AC-001, AC-002, AC-003: Theme CSS (light + dark + system support)
- **Complexity:** Medium
- **Effort:** 1.5h
- **Tasks:** TASK-001, TASK-002
- **Strategy:** Keep existing `:root` as light theme. Add `[data-theme="dark"]` overrides. Convert hardcoded colors in CSS to variables where needed.

### AC-004, AC-005, AC-006: Theme JavaScript (system detection, persistence, defaults)
- **Complexity:** Medium
- **Effort:** 1h
- **Tasks:** TASK-003
- **Strategy:** Single `theme.js` script handles localStorage read/write, `matchMedia` listener for system preference, and `data-theme` attribute management.

### AC-007, AC-008, AC-010: Settings page (route, template, header nav)
- **Complexity:** Simple
- **Effort:** 1.5h
- **Tasks:** TASK-004, TASK-005, TASK-006
- **Strategy:** New FastAPI route at `/settings`, new Jinja2 template extending `base.html`, settings link added to header.

### AC-009: Immediate theme application
- **Complexity:** Simple
- **Effort:** Included in TASK-003
- **Strategy:** JavaScript applies `data-theme` attribute instantly on selection change. CSS variables cascade immediately.

### AC-011: FOUC prevention
- **Complexity:** Simple
- **Effort:** Included in TASK-003
- **Strategy:** Inline `<script>` in `<head>` of `base.html` reads localStorage before CSS paints.

### AC-012: All existing UI elements render correctly in both themes
- **Complexity:** Medium
- **Effort:** 1h
- **Tasks:** TASK-002 (covered during dark CSS work)
- **Strategy:** Audit all hardcoded colors in CSS and templates. Convert to CSS variables. Test modals, badges, tables, filters.

### AC-013: Chart.js theme adaptation
- **Complexity:** Medium
- **Effort:** 0.5h
- **Tasks:** TASK-007
- **Strategy:** Read computed CSS variable values in JS and pass to Chart.js config. Re-render charts on theme change.

## Implementation Phases

### Phase 1: CSS Theme System (1.5h)

Foundation — dark theme CSS and hardcoded color cleanup.

| Task ID | Description | Effort | Dependencies | AC Coverage |
|---------|-------------|--------|--------------|-------------|
| TASK-001 | Add `[data-theme="dark"]` CSS variable overrides to `styles.css` | 45min | None | AC-001, AC-003 |
| TASK-002 | Convert remaining hardcoded colors to CSS variables (table head bg, row hover, file list bg, modal header bg, badge colors) | 45min | TASK-001 | AC-002, AC-003, AC-012 |

**Files modified:**
- `app/static/css/styles.css`

### Phase 2: Theme JavaScript (1h)

Client-side logic — localStorage, OS detection, FOUC prevention.

| Task ID | Description | Effort | Dependencies | AC Coverage |
|---------|-------------|--------|--------------|-------------|
| TASK-003 | Create `app/static/js/theme.js` — theme manager with localStorage persistence, `matchMedia` listener, `data-theme` attribute management. Add inline FOUC-prevention script to `base.html` `<head>`. | 1h | TASK-001 | AC-004, AC-005, AC-006, AC-009, AC-011 |

**Files created:**
- `app/static/js/theme.js`

**Files modified:**
- `app/templates/base.html` (inline FOUC script in `<head>`, `<script>` tag for theme.js)

### Phase 3: Settings Page (1.5h)

New route, template, and header navigation.

| Task ID | Description | Effort | Dependencies | AC Coverage |
|---------|-------------|--------|--------------|-------------|
| TASK-004 | Add `GET /settings` route in `app/main.py` | 15min | None | AC-007 |
| TASK-005 | Create `app/templates/settings.html` with theme toggle (segmented control: Light / Dark / System), structured with card-based sections for future expansion | 45min | TASK-003, TASK-004 | AC-007, AC-010 |
| TASK-006 | Add "Settings" navigation link to header in `app/templates/base.html` | 15min | TASK-004 | AC-008 |
| TASK-007 | Update Chart.js rendering in `charts.html` to read theme-aware colors and re-render on theme change | 30min | TASK-003 | AC-013 |

**Files created:**
- `app/templates/settings.html`

**Files modified:**
- `app/main.py` (new route)
- `app/templates/base.html` (header nav link)
- `app/templates/partials/charts.html` (theme-aware colors)

### Phase 4: Testing & Polish (1h)

Verify all elements, write tests for the settings route.

| Task ID | Description | Effort | Dependencies | AC Coverage |
|---------|-------------|--------|--------------|-------------|
| TASK-008 | Write test for `GET /settings` route returns 200 | 15min | TASK-004 | AC-007 |
| TASK-009 | Manual verification: test all UI components in both themes (table, modals, badges, filters, charts, empty states, pagination) | 30min | Phase 1-3 complete | AC-012 |
| TASK-010 | Add print media query to force light theme | 15min | TASK-001 | Edge case |

**Files modified:**
- `tests/test_api.py` (or new test file)
- `app/static/css/styles.css` (print media query)

## Effort Summary

| Phase | Estimated Hours |
|-------|-----------------|
| Phase 1: CSS Theme System | 1.5h |
| Phase 2: Theme JavaScript | 1h |
| Phase 3: Settings Page | 1.5h |
| Phase 4: Testing & Polish | 1h |
| **Total** | **5h** |

## File Change Summary

| File | Action | Phase |
|------|--------|-------|
| `app/static/css/styles.css` | Modify (dark theme overrides, variable cleanup, print query) | 1, 4 |
| `app/static/js/theme.js` | Create (theme manager) | 2 |
| `app/templates/base.html` | Modify (FOUC script, theme.js include, settings nav link) | 2, 3 |
| `app/templates/settings.html` | Create (settings page) | 3 |
| `app/main.py` | Modify (add /settings route) | 3 |
| `app/templates/partials/charts.html` | Modify (theme-aware chart colors) | 3 |
| `tests/test_api.py` | Modify (settings route test) | 4 |

## Dependencies

- **None external.** All work uses existing CSS variables architecture.
- TASK-001 (dark CSS) must complete before TASK-003 (JS) and TASK-005 (template) can be validated.
- TASK-003 (theme.js) must exist before TASK-005 (settings page) can wire up the toggle.
- TASK-004 (route) must exist before TASK-005 (template) can be served.

## Critical Path

```
TASK-001 → TASK-002 → TASK-003 → TASK-005 → TASK-009
                         ↓
                       TASK-007
```

TASK-004 and TASK-006 are independent and can slot in anytime.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Hardcoded colors missed in dark theme | Medium | Low | Systematic audit of all CSS selectors; visual test both themes |
| Chart.js doesn't re-render cleanly on theme change | Low | Medium | Destroy and recreate chart instances on theme change |
| FOUC on slow connections | Low | Low | Inline script in `<head>` runs synchronously before paint |

## Spec Traceability

| Task | Acceptance Criteria |
|------|-------------------|
| TASK-001 | AC-001, AC-003 |
| TASK-002 | AC-002, AC-003, AC-012 |
| TASK-003 | AC-004, AC-005, AC-006, AC-009, AC-011 |
| TASK-004 | AC-007 |
| TASK-005 | AC-007, AC-010 |
| TASK-006 | AC-008 |
| TASK-007 | AC-013 |
| TASK-008 | AC-007 |
| TASK-009 | AC-012 |
| TASK-010 | Edge case (print) |

## Next Steps

1. Review and approve this plan
2. Run `/add:tdd-cycle specs/dark-mode.md` to begin implementation
