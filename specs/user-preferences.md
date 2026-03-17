# Spec: User Preferences

**Version:** 0.1.0
**Created:** 2026-03-01
**PRD Reference:** docs/prd.md
**Status:** Complete

## 1. Overview

Persist user preferences (starting with theme) in the database so settings follow users across browsers and devices. Uses a JSON column for future-proofing — theme is the first preference, others can be added without schema changes. Unauthenticated users keep the existing localStorage behavior. Logged-in users get their preference injected server-side to avoid flash.

### User Story

As a logged-in user, I want my theme preference to persist in my account, so that I see the same theme when I log in from a different browser or device.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | User model has a `preferences` JSON column with default `{}` | Must |
| AC-002 | `preferences` column stores `{"theme": "light\|dark\|system"}` (and is extensible for future keys) | Must |
| AC-003 | `PATCH /api/v1/users/me/preferences` accepts a partial JSON object and merges it into the user's preferences | Must |
| AC-004 | `GET /api/v1/users/me/preferences` returns the user's full preferences object | Must |
| AC-005 | When a logged-in user loads any page, the server injects their theme preference into the inline `<script>` block in `<head>` | Must |
| AC-006 | When the injected server preference is present, it overrides localStorage (DB is source of truth for logged-in users) | Must |
| AC-007 | When the user clicks a theme button, localStorage is updated immediately and a background `PATCH` request saves to the API | Must |
| AC-008 | If the background PATCH fails, the theme still works locally (fire-and-forget) | Must |
| AC-009 | Unauthenticated users (or auth disabled) use the existing localStorage-only behavior with no API calls | Must |
| AC-010 | The preferences API endpoints require authentication (any role) | Must |
| AC-011 | Invalid preference values (e.g., `{"theme": "rainbow"}`) return 422 with a clear error message | Should |
| AC-012 | Alembic migration adds the `preferences` column to the `users` table | Must |

## 3. User Test Cases

### TC-001: Theme persists across browsers

**Precondition:** User is logged in, theme is set to "dark"
**Steps:**
1. On Browser A, click the "dark" theme button in Settings
2. Open Browser B (fresh, no localStorage for this site)
3. Log in as the same user
4. Navigate to Settings
**Expected Result:** Theme is "dark", the dark theme button is highlighted, page rendered in dark mode with no flash
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-002: Unauthenticated user uses localStorage

**Precondition:** Auth is enabled, user is not logged in
**Steps:**
1. Navigate to the login page
2. Click the theme toggle (if visible) or set localStorage `theme=dark` manually
3. Refresh the page
**Expected Result:** Dark theme persists via localStorage. No API calls to preferences endpoint.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-003: DB preference overrides localStorage on login

**Precondition:** User's DB preference is "light". Browser localStorage has "dark".
**Steps:**
1. Log in as the user
2. Observe the theme
**Expected Result:** Theme is "light" (DB wins). localStorage is updated to "light".
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-004: Fire-and-forget save on theme toggle

**Precondition:** User is logged in
**Steps:**
1. Click "dark" theme button
2. Observe theme changes immediately
3. Check network tab — a PATCH request is sent in the background
**Expected Result:** Theme applies instantly. PATCH request fires but UI does not wait for response.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-005: API failure doesn't break theme

**Precondition:** User is logged in, API is unreachable (simulated)
**Steps:**
1. Click "light" theme button
2. API call fails (network error)
**Expected Result:** Theme still changes to light via localStorage. No error shown to user.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

## 4. Data Model

### User (existing — modify)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| preferences | JSON | No (default `{}`) | User preferences as a JSON object. Keys: `theme` (string: "light", "dark", "system"). Extensible for future settings. |

### Preferences Schema (validation, not a DB table)

| Key | Type | Valid Values | Default |
|-----|------|-------------|---------|
| theme | string | "light", "dark", "system" | "system" |

### Relationships

No new relationships. The `preferences` column is added to the existing `users` table.

## 5. API Contract

### PATCH /api/v1/users/me/preferences

**Description:** Merge partial preferences into the current user's preferences.

**Request:**
```json
{
    "theme": "dark"
}
```

**Response (200):**
```json
{
    "theme": "dark"
}
```

**Error Responses:**
- `401` — Not authenticated
- `422` — Invalid preference value (e.g., `{"theme": "rainbow"}`)

### GET /api/v1/users/me/preferences

**Description:** Get the current user's full preferences object.

**Response (200):**
```json
{
    "theme": "dark"
}
```

**Error Responses:**
- `401` — Not authenticated

## 6. UI Behavior

### Theme Toggle (existing — modify)

- **No auth / auth disabled:** Current behavior unchanged. localStorage only, no API calls.
- **Logged in:** Click applies theme instantly (localStorage), fires background PATCH to API.
- **Page load (logged in):** Server injects `window.__USER_THEME__ = "dark"` (or whichever value) into the inline `<head>` script. JS reads this before localStorage.
- **Page load (not logged in):** Existing localStorage fallback.

### Server-Side Injection

The inline script in `<head>` (currently in base.html, login.html, etc.) changes from:

```javascript
var theme = localStorage.getItem('theme') || 'system';
```

to:

```javascript
var theme = window.__USER_THEME__ || localStorage.getItem('theme') || 'system';
```

The Jinja template sets `window.__USER_THEME__` only when a user is authenticated and has a theme preference.

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| User has no `preferences` row (existing users) | Default `{}` — treated as "system" theme |
| `preferences` column is `null` | Treated same as `{}` |
| Unknown keys in PATCH body | Ignored (only known keys like `theme` are persisted) |
| Empty PATCH body `{}` | 200, no changes, return current preferences |
| User logs out | Theme stays at whatever localStorage has (no clearing) |
| Multiple rapid theme toggles | Each fires a PATCH; last one wins in DB (no debounce needed — idempotent) |
| Auth disabled globally | No injection, no API calls, pure localStorage |

## 8. Dependencies

- Alembic for migration (already in use)
- Existing JWT auth middleware (`get_current_user`)
- Existing theme.js ThemeManager

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-01 | 0.1.0 | Claude | Initial spec from /add:spec interview |
