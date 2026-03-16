# Spec: Changelog Presentation Improvements

**Version:** 0.1.0
**Created:** 2026-03-04
**PRD Reference:** docs/prd.md
**Status:** Complete

## 1. Overview

The in-app changelog (Settings > Changelog tab) currently renders parsed CHANGELOG.md entries with minimal styling — plain text items, inline styles, no markdown rendering, and a clunky accordion UX. This spec improves the visual presentation with proper hierarchy, color-coded section badges, markdown rendering in list items, a polished accordion, and pagination to keep the list manageable as versions accumulate.

### User Story

As an **operator or admin**, I want the in-app changelog to be well-formatted and easy to scan, so that I can quickly understand what changed in each release without reading raw markdown text.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Changelog version headers display version number, date, and "Current" badge with clear visual hierarchy (larger font, bold, distinct from content) | Must |
| AC-002 | Section headers (Added, Fixed, Changed, Documentation, etc.) display as color-coded badges: Added=green, Fixed=blue, Changed=amber, Documentation=gray, Removed=red | Must |
| AC-003 | Markdown formatting in list items is rendered as HTML (bold `**text**`, inline code `` `text` ``, links, nested sub-items) instead of raw text | Must |
| AC-004 | The current app version's entry auto-expands on load; all other versions start collapsed | Must |
| AC-005 | Accordion expand/collapse is smooth (CSS transition) and works without a full HTMX round-trip for already-loaded content | Must |
| AC-006 | Only the most recent 5 versions are shown initially; a "Show older versions" button loads the rest | Must |
| AC-007 | Changelog styles use CSS classes (not inline styles) and respect the app's dark/light theme | Should |
| AC-008 | Multi-line changelog items (sub-lists with indented `-` lines) are parsed and rendered as nested `<ul>` elements | Should |

## 3. User Test Cases

### TC-001: Changelog loads with current version expanded

**Precondition:** User is logged in as operator or admin, app is running v2.0.0
**Steps:**
1. Navigate to /settings
2. Click the "Changelog" tab
**Expected Result:** Changelog loads. Version 2.0.0 is auto-expanded showing its sections. Other versions are collapsed showing only version + date header.
**Screenshot Checkpoint:** tests/screenshots/changelog/step-01-initial-load.png
**Maps to:** TBD

### TC-002: Section badges are color-coded

**Precondition:** Changelog tab is visible with current version expanded
**Steps:**
1. Look at the expanded version's section headers
**Expected Result:** "Added" has a green badge, "Fixed" has a blue badge, "Changed" has an amber/yellow badge, "Documentation" has a gray badge.
**Screenshot Checkpoint:** tests/screenshots/changelog/step-02-section-badges.png
**Maps to:** TBD

### TC-003: Markdown renders in items

**Precondition:** Changelog tab is visible with a version expanded
**Steps:**
1. Look at items containing `**bold text**` or `` `code` `` in the CHANGELOG.md source
**Expected Result:** Bold text renders as `<strong>`, inline code renders as `<code>` with monospace styling. No raw `**` or backtick characters visible.
**Screenshot Checkpoint:** tests/screenshots/changelog/step-03-markdown-rendering.png
**Maps to:** TBD

### TC-004: Accordion expand/collapse

**Precondition:** Changelog is loaded with only current version expanded
**Steps:**
1. Click on a collapsed version header (e.g., 1.11.0)
2. Observe it expands with content
3. Click the same header again
4. Observe it collapses
**Expected Result:** Smooth expand/collapse animation. Content toggles visibility. No page reload or visible loading spinner for already-fetched content.
**Screenshot Checkpoint:** tests/screenshots/changelog/step-04-accordion-toggle.png
**Maps to:** TBD

### TC-005: Show older versions

**Precondition:** Changelog has more than 5 versions
**Steps:**
1. Open the changelog tab
2. Observe only 5 versions are listed
3. Click "Show older versions" button
**Expected Result:** Remaining versions appear below the initial 5. Button disappears or changes to indicate all versions are shown.
**Screenshot Checkpoint:** tests/screenshots/changelog/step-05-show-older.png
**Maps to:** TBD

## 4. Data Model

No data model changes. The existing `ChangelogVersion` Pydantic model is sufficient:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | str | Yes | Version string (e.g., "2.0.0") |
| date | str \| None | No | Release date (e.g., "2026-03-03") |
| sections | dict[str, list[str]] | Yes | Section name → list of items |

### Parser Enhancement

The changelog parser needs to handle multi-line items (indented sub-lists under a top-level `-` item) by joining continuation lines or producing nested structures.

## 5. API Contract

### GET /htmx/changelog

**Description:** Returns the changelog version list partial (unchanged endpoint, updated template).

**Query Parameters:**
- `show_all` (optional, bool, default=false): When true, returns all versions. When false, returns only the most recent 5.

**Response (200):** HTML partial with changelog version accordion.

### GET /htmx/changelog/{version}

**Description:** Returns expanded content for a specific version (unchanged endpoint, updated template with markdown rendering and badges).

**Response (200):** HTML partial with color-coded section badges and rendered markdown items.

## 6. UI Behavior

### States

- **Loading:** Skeleton placeholder or spinner while HTMX fetches changelog list
- **Empty:** "No changelog entries found" message
- **Error:** Generic error message if CHANGELOG.md is missing or unparseable
- **Success:** Accordion list with current version auto-expanded

### Section Badge Colors

| Section | Badge Color | CSS Class |
|---------|-------------|-----------|
| Added | Green (#22c55e) | `badge-added` |
| Fixed | Blue (#3b82f6) | `badge-fixed` |
| Changed | Amber (#f59e0b) | `badge-changed` |
| Removed | Red (#ef4444) | `badge-removed` |
| Documentation | Gray (#6b7280) | `badge-docs` |
| GA Promotion | Purple (#8b5cf6) | `badge-promotion` |
| Other | Default gray | `badge-default` |

### Accordion Behavior

- Version headers have a chevron indicator (▶ collapsed, ▼ expanded)
- Current version auto-expands on initial load (content fetched via HTMX)
- Clicking an expanded header collapses it (client-side toggle, no re-fetch)
- Clicking a collapsed header fetches content via HTMX if not yet loaded, or toggles visibility if already loaded
- Smooth height transition (max-height or similar CSS approach)

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| CHANGELOG.md missing | "No changelog available" message, no error |
| Version has no sections | Version header still renders, empty body |
| Fewer than 5 versions exist | Show all versions, no "Show older" button |
| Unknown section name (e.g., "Security") | Render with default gray badge |
| Item text contains HTML entities | Escape properly to prevent XSS |
| Very long item text | Word-wrap within the container |

## 8. Dependencies

- Existing changelog parser (`app/services/changelog_parser.py`)
- Existing changelog schema (`app/schemas/changelog.py`)
- Existing HTMX changelog routes (`app/routes/pages.py`)
- App's CSS theme system (dark/light mode CSS variables)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-04 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
