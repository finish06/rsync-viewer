# Spec: Changelog Viewer

**Version:** 0.1.0
**Created:** 2026-02-24
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Add a changelog viewer tab to the settings page that parses CHANGELOG.md and displays version history with expandable accordion sections. Users can see what's new in each release, with the current running version highlighted. Changes are grouped by type (Added, Fixed, Changed, Documentation) matching the Keep a Changelog format.

### User Story

As a homelab administrator, I want to see what changed in each version of rsync-viewer, so that I can understand new features and fixes after updating.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A "Changelog" tab appears on the settings page when CHANGELOG.md exists and is parseable | Must |
| AC-002 | Each version from CHANGELOG.md is displayed as a collapsible accordion header showing version number and date | Must |
| AC-003 | Clicking a version header expands/collapses its content via HTMX without page reload | Must |
| AC-004 | Expanded version content shows changes grouped by section (Added, Fixed, Changed, Documentation) | Must |
| AC-005 | The version matching the running application version displays a "Current" badge | Must |
| AC-006 | The changelog tab is hidden entirely when CHANGELOG.md is missing or cannot be parsed | Must |
| AC-007 | The "Unreleased" section from CHANGELOG.md is displayed at the top if it has content | Should |
| AC-008 | The CHANGELOG.md parser handles all section types defined in Keep a Changelog format | Should |

## 3. User Test Cases

### TC-001: View changelog and expand a version

**Precondition:** Application is running, CHANGELOG.md exists with multiple versions
**Steps:**
1. Navigate to the settings page
2. Click the "Changelog" tab
3. Click on the "v1.7.0" version header
**Expected Result:** The v1.7.0 section expands showing Added, Fixed, Changed subsections with bullet points. Other versions remain collapsed.
**Screenshot Checkpoint:** tests/screenshots/changelog/step-01-version-expanded.png
**Maps to:** TBD

### TC-002: Current version badge

**Precondition:** Application is running version 1.7.0, CHANGELOG.md contains v1.7.0 entry
**Steps:**
1. Navigate to settings page
2. Click the "Changelog" tab
3. Observe the version list
**Expected Result:** The v1.7.0 header displays a "Current" badge next to the version number. Other versions do not have this badge.
**Screenshot Checkpoint:** tests/screenshots/changelog/step-02-current-badge.png
**Maps to:** TBD

### TC-003: Missing changelog file

**Precondition:** CHANGELOG.md does not exist or is empty
**Steps:**
1. Navigate to the settings page
2. Observe the available tabs
**Expected Result:** The "Changelog" tab is not visible in the settings page tab bar.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-004: Accordion toggle behavior

**Precondition:** Application is running, changelog tab is active
**Steps:**
1. Click version v1.7.0 to expand it
2. Click version v1.6.0 to expand it
3. Click version v1.7.0 again to collapse it
**Expected Result:** Multiple versions can be expanded simultaneously. Clicking an expanded version collapses it.
**Screenshot Checkpoint:** tests/screenshots/changelog/step-03-multiple-expanded.png
**Maps to:** TBD

## 4. Data Model

### ChangelogVersion (in-memory, parsed from CHANGELOG.md)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | str | Yes | Version string (e.g. "1.7.0") or "Unreleased" |
| date | str \| None | No | Release date (e.g. "2026-02-24"), None for Unreleased |
| sections | dict[str, list[str]] | Yes | Map of section name ("Added", "Fixed", etc.) to list of change descriptions |

### Relationships

No database entities. `ChangelogVersion` is a Pydantic model parsed from CHANGELOG.md at request time (or cached).

## 5. API Contract

### GET /settings/changelog (HTMX partial)

**Description:** Returns the changelog tab content as an HTML partial for HTMX swap.

**Response (200):** HTML partial containing the version accordion list.

**Error Responses:**
- Returns empty response if CHANGELOG.md is missing (tab should not be visible)

### GET /settings/changelog/{version} (HTMX partial)

**Description:** Returns the expanded content for a specific version as an HTML partial.

**Response (200):** HTML partial containing grouped change sections for the requested version.

**Error Responses:**
- `404` — Version not found in CHANGELOG.md

## 6. UI Behavior

### States

- **Loading:** HTMX loading indicator on the changelog tab content area
- **Empty:** Tab is hidden entirely (AC-006)
- **Error:** Tab is hidden entirely if parsing fails
- **Success:** Version list with accordion headers, "Current" badge on matching version

### Screenshot Checkpoints

| Step | Description | Path |
|------|-------------|------|
| 1 | Version expanded with grouped changes | tests/screenshots/changelog/step-01-version-expanded.png |
| 2 | Current version badge visible | tests/screenshots/changelog/step-02-current-badge.png |
| 3 | Multiple versions expanded | tests/screenshots/changelog/step-03-multiple-expanded.png |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| CHANGELOG.md missing | Changelog tab hidden from settings page |
| CHANGELOG.md empty or unparseable | Changelog tab hidden from settings page |
| Unreleased section has no content | Unreleased header not shown |
| Version has empty sections | Section header not shown for that version |
| Running version not found in changelog | No "Current" badge shown on any version |
| Very long changelog (20+ versions) | All versions rendered, most recent first, all collapsed by default |

## 8. Dependencies

- Existing settings page with tab navigation (app/templates/settings.html)
- CHANGELOG.md in project root (already exists, follows Keep a Changelog format)
- Application version from app/config.py or pyproject.toml

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-24 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
