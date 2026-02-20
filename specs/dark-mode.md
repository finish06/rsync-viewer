# Spec: Dark Mode & Theme Settings

**Version:** 0.1.0
**Created:** 2026-02-19
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

A theme system for the Rsync Log Viewer dashboard that supports light, dark, and system (OS-preference) modes. Users toggle between themes via a new settings page. The existing dashboard serves as the light theme; a dark theme is derived from it. The user's preference is persisted in localStorage and defaults to "system" for first-time visitors.

### User Story

As a homelab administrator, I want to switch the dashboard between light and dark themes, so that I can use it comfortably in different lighting conditions and match my OS preference.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | The dashboard supports three theme modes: light, dark, and system | Must |
| AC-002 | The light theme matches the current existing dashboard appearance | Must |
| AC-003 | The dark theme provides a dark background with light text, derived from the existing light palette | Must |
| AC-004 | When "system" is selected, the theme follows the user's OS `prefers-color-scheme` media query | Must |
| AC-005 | The selected theme preference is persisted in localStorage and restored on page load | Must |
| AC-006 | First-time visitors (no localStorage value) default to "system" mode | Must |
| AC-007 | A settings page exists at `/settings` with a theme toggle (light / dark / system) | Must |
| AC-008 | The settings page is navigable from the header (e.g., a gear icon or "Settings" link) | Must |
| AC-009 | Theme changes apply immediately without a full page reload | Should |
| AC-010 | The settings page is structured to accommodate future settings sections | Should |
| AC-011 | There is no visible flash of incorrect theme on page load (FOUC prevention) | Should |
| AC-012 | All existing UI elements (tables, modals, charts, filters, badges) render correctly in both themes | Must |
| AC-013 | Chart.js charts adapt their colors to the active theme | Should |

## 3. User Test Cases

### TC-001: Toggle to Dark Mode

**Precondition:** User is on the dashboard with light theme active.
**Steps:**
1. Click the "Settings" link in the header
2. On the settings page, select "Dark" from the theme options
3. Observe the page appearance changes immediately
4. Navigate back to the dashboard
**Expected Result:** The entire dashboard (header, tables, cards, modals, charts) renders with dark theme colors. The setting persists — refreshing the page keeps dark mode.
**Screenshot Checkpoint:** tests/screenshots/dark-mode/step-01-dark-theme-active.png
**Maps to:** TBD

### TC-002: Toggle to Light Mode

**Precondition:** User is on the dashboard with dark theme active.
**Steps:**
1. Navigate to the settings page
2. Select "Light" from the theme options
3. Observe the page appearance changes immediately
**Expected Result:** The dashboard returns to the original light theme appearance.
**Screenshot Checkpoint:** tests/screenshots/dark-mode/step-02-light-theme-active.png
**Maps to:** TBD

### TC-003: System Mode Follows OS Preference

**Precondition:** User has not set a preference (first visit) or selects "System".
**Steps:**
1. Set OS to dark mode
2. Load the dashboard
3. Verify dark theme is applied
4. Change OS to light mode
5. Verify theme updates to light (either on reload or reactively via `matchMedia` listener)
**Expected Result:** The theme matches the OS preference automatically.
**Screenshot Checkpoint:** tests/screenshots/dark-mode/step-03-system-mode.png
**Maps to:** TBD

### TC-004: Preference Persists Across Sessions

**Precondition:** User has selected "Dark" on the settings page.
**Steps:**
1. Close the browser tab
2. Reopen the dashboard URL
**Expected Result:** Dark theme is applied immediately on load with no flash of light theme.
**Screenshot Checkpoint:** tests/screenshots/dark-mode/step-04-persistence.png
**Maps to:** TBD

### TC-005: Settings Page Layout

**Precondition:** None.
**Steps:**
1. Navigate to `/settings`
**Expected Result:** The settings page shows a "Theme" section with three options (Light, Dark, System) and has visual structure that can accommodate future settings sections (e.g., headings, card-based layout).
**Screenshot Checkpoint:** tests/screenshots/dark-mode/step-05-settings-page.png
**Maps to:** TBD

## 4. Data Model

No database changes required. Theme preference is stored client-side in localStorage.

### Client Storage

| Key | Type | Values | Default | Description |
|-----|------|--------|---------|-------------|
| `theme` | string | `light`, `dark`, `system` | `system` | User's selected theme preference |

## 5. API Contract

### GET /settings

**Description:** Render the settings page.

**Response (200):** HTML page with theme toggle UI.

No REST API changes are needed — this is a server-rendered page. Theme switching is handled entirely client-side via JavaScript and CSS.

## 6. UI Behavior

### Theme CSS Strategy

The existing `:root` CSS variables define the light theme. A `[data-theme="dark"]` attribute on `<html>` overrides these variables with dark equivalents. The JavaScript sets this attribute based on the user's preference or OS media query.

### Dark Theme Palette (derived from light)

| Variable | Light Value | Dark Value |
|----------|-------------|------------|
| `--bg-color` | `#f9fafb` | `#111827` |
| `--card-bg` | `#ffffff` | `#1f2937` |
| `--border-color` | `#e5e7eb` | `#374151` |
| `--text-color` | `#111827` | `#f9fafb` |
| `--text-muted` | `#6b7280` | `#9ca3af` |
| `--primary-color` | `#2563eb` | `#3b82f6` |
| `--primary-hover` | `#1d4ed8` | `#2563eb` |
| `--success-color` | `#10b981` | `#34d399` |
| `--danger-color` | `#ef4444` | `#f87171` |
| Table head bg | `#f3f4f6` | `#1f2937` |
| Row hover bg | `#f9fafb` | `#374151` |
| Source badge bg | `#dbeafe` | `#1e3a5f` |
| Source badge text | `#1e40af` | `#93c5fd` |
| Dry run badge bg | `#fef3c7` | `#78350f` |
| Dry run badge text | `#92400e` | `#fde68a` |

### States

- **Loading:** Settings page renders with current theme already applied (no loading state needed).
- **Empty:** N/A — settings page always has content.
- **Error:** N/A — no server interaction for theme changes.
- **Success:** Theme applies instantly. No success toast needed — the visual change is the confirmation.

### Settings Page Structure

```
Settings
├── Appearance
│   └── Theme: [Light] [Dark] [System]  (radio group or segmented control)
└── (Future sections placeholder — empty for now)
```

### FOUC Prevention

A small inline `<script>` in `<head>` (before CSS loads) reads localStorage and sets `data-theme` on `<html>` immediately, preventing any flash of the wrong theme.

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| localStorage is cleared or unavailable | Fall back to "system" mode |
| Browser doesn't support `prefers-color-scheme` | "System" mode falls back to light theme |
| User switches OS theme while page is open (system mode) | Theme updates reactively via `matchMedia` change listener |
| Chart.js canvas doesn't pick up CSS variable changes | Re-render charts when theme changes, or use JS to read computed CSS variable values |
| Modal is open when theme switches | Modal and backdrop colors update immediately via CSS variables |
| Print mode | Print styles should use light theme regardless of setting |

## 8. Dependencies

- No external dependencies required
- Builds on existing CSS custom properties architecture in `app/static/css/styles.css`
- Requires a new Jinja2 template for the settings page
- Requires a new FastAPI route for `/settings`

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-19 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
