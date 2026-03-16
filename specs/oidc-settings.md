# Spec: OIDC Settings UI

**Version:** 0.2.0
**Created:** 2026-02-26
**PRD Reference:** docs/prd.md
**Supersedes:** specs/oidc-authentication.md AC-009 (env var configuration)
**Related:** specs/oidc-authentication.md (OIDC login flow, user creation/linking)
**Status:** Complete
**Milestone:** M7 — OIDC Authentication

## 1. Overview

Move OIDC provider configuration from environment variables to an admin-only UI in the Settings page. Admins can configure the OIDC provider details (issuer URL, client ID, client secret, provider name), toggle OIDC on/off, toggle "Hide Local Login" mode, test OIDC discovery, and manage the full lifecycle of OIDC configuration — all from the browser. A `FORCE_LOCAL_LOGIN` environment variable serves as a safety fallback to always show the local login form regardless of UI settings.

### User Story

As an Admin, I want to configure OIDC authentication through the settings UI, so that I can set up and manage single sign-on without editing environment variables or restarting the application.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Admin can configure OIDC provider via UI: issuer URL, client ID, client secret, provider name | Must |
| AC-002 | Admin can toggle OIDC enabled/disabled | Must |
| AC-003 | Admin can toggle "Hide Local Login" (OIDC-only mode) | Must |
| AC-004 | `FORCE_LOCAL_LOGIN=true` env var overrides "Hide Local Login" — local login form is always shown when set | Must |
| AC-005 | Client secret is encrypted at rest using Fernet symmetric encryption (same pattern as SMTP config) | Must |
| AC-006 | Client secret is masked in the UI when retrieving saved configuration (displayed as `••••••••`) | Must |
| AC-007 | Admin can test OIDC discovery — verifies issuer URL resolves `/.well-known/openid-configuration` and displays discovered endpoints | Must |
| AC-008 | Non-admin users cannot see the Authentication section in Settings | Must |
| AC-009 | Non-admin users cannot access Authentication endpoints (403) | Must |
| AC-010 | OIDC login flow reads config from DB instead of environment variables | Must |
| AC-011 | Save is allowed even if discovery test fails (admin may configure before provider is live) | Should |
| AC-012 | Empty client secret on edit preserves the existing encrypted value (no accidental wipe) | Should |
| AC-013 | A small info note in the UI explains the `FORCE_LOCAL_LOGIN` safety fallback | Should |
| AC-014 | When OIDC is disabled via toggle, existing OIDC sessions remain valid until expiry but no new OIDC logins are allowed | Should |
| AC-015 | OIDC settings UI displays the callback URL (`/auth/oidc/callback`) so the admin knows what to configure in their OIDC provider | Should |
| AC-016 | The Callback URL info box and `FORCE_LOCAL_LOGIN` info note render correctly in both light and dark mode — no white/light boxes on dark backgrounds. Info boxes must use theme-aware CSS variables (`--card-bg` or a new `--bg-secondary`) instead of hardcoded light colors | Must |
| AC-017 | All inline `background: var(--bg-secondary, #f5f5f5)` styles in the OIDC template are replaced with a proper CSS class that respects dark mode theming | Must |

## 3. User Test Cases

### TC-001: Admin configures OIDC for the first time

**Precondition:** Admin is logged in. No OIDC configuration exists.
**Steps:**
1. Navigate to Settings
2. Locate the "Authentication" section
3. Fill in Issuer URL (`https://auth.example.com`), Client ID (`rsync-viewer`), Client Secret, Provider Name (`PocketId`)
4. Click "Test Discovery"
5. See green confirmation with discovered endpoints (authorize, token, userinfo)
6. Toggle "Enable OIDC" on
7. Click "Save"
**Expected Result:** Success toast: "OIDC configuration saved." Form shows saved values with client secret masked. Login page now shows "Login with PocketId" button.
**Screenshot Checkpoint:** tests/screenshots/oidc-settings/step-01-oidc-configured.png
**Maps to:** TBD

### TC-002: Admin tests OIDC discovery with valid issuer

**Precondition:** Admin is logged in. Authentication section is visible.
**Steps:**
1. Enter a valid Issuer URL
2. Click "Test Discovery"
**Expected Result:** Green confirmation showing discovered endpoints: authorization_endpoint, token_endpoint, userinfo_endpoint. No secrets exposed in the response.
**Screenshot Checkpoint:** tests/screenshots/oidc-settings/step-02-discovery-success.png
**Maps to:** TBD

### TC-003: Admin tests OIDC discovery with invalid issuer

**Precondition:** Admin is logged in. Authentication section is visible.
**Steps:**
1. Enter an invalid or unreachable Issuer URL (`https://nonexistent.example.com`)
2. Click "Test Discovery"
**Expected Result:** Error message showing the connection failure (e.g., "Discovery failed: Could not reach issuer URL"). No credentials exposed in the error.
**Screenshot Checkpoint:** tests/screenshots/oidc-settings/step-03-discovery-failed.png
**Maps to:** TBD

### TC-004: Admin enables "Hide Local Login" with FORCE_LOCAL_LOGIN override

**Precondition:** Admin has OIDC configured and enabled. `FORCE_LOCAL_LOGIN=true` is set in the environment.
**Steps:**
1. Navigate to Settings > Authentication
2. Toggle "Hide Local Login" on
3. Click "Save"
4. Navigate to `/login`
**Expected Result:** Login page still shows both the local login form AND the OIDC button because `FORCE_LOCAL_LOGIN=true` overrides the hide setting. Info note in Authentication section mentions this override.
**Screenshot Checkpoint:** tests/screenshots/oidc-settings/step-04-force-local-override.png
**Maps to:** TBD

### TC-005: Admin disables OIDC

**Precondition:** Admin has OIDC configured and enabled. Users have active OIDC sessions.
**Steps:**
1. Navigate to Settings > Authentication
2. Toggle "Enable OIDC" off
3. Click "Save"
4. Navigate to `/login`
**Expected Result:** Login page no longer shows the OIDC button. Existing OIDC sessions remain valid until they expire. Configuration is preserved in DB (not deleted) for easy re-enable.
**Screenshot Checkpoint:** tests/screenshots/oidc-settings/step-05-oidc-disabled.png
**Maps to:** TBD

### TC-006: Admin edits OIDC configuration (keeps existing secret)

**Precondition:** Admin has OIDC configured.
**Steps:**
1. Navigate to Settings > Authentication
2. Change Provider Name from "PocketId" to "Authelia"
3. Leave Client Secret field empty
4. Click "Save"
**Expected Result:** Provider Name updated. Client secret remains unchanged (not wiped). Login page shows "Login with Authelia".
**Screenshot Checkpoint:** tests/screenshots/oidc-settings/step-06-edited.png
**Maps to:** TBD

### TC-007: Non-admin cannot access Authentication settings

**Precondition:** User with Operator or Viewer role is logged in.
**Steps:**
1. Navigate to Settings
**Expected Result:** Authentication section is not visible. Direct URL/HTMX request to authentication endpoints returns 403.
**Screenshot Checkpoint:** tests/screenshots/oidc-settings/step-07-non-admin-denied.png
**Maps to:** TBD

### TC-008: OIDC settings dark mode rendering

**Precondition:** Admin is logged in. Theme is set to dark mode. OIDC is configured.
**Steps:**
1. Navigate to Settings > Authentication
2. Observe the Callback URL info box at the top
3. Observe the `FORCE_LOCAL_LOGIN` info note below the toggles
**Expected Result:** Both info boxes have a dark background consistent with the dark theme (e.g., `--card-bg` / `#1f2937` or similar). Text is readable. No white or light-colored boxes that contrast harshly with the dark page background.
**Screenshot Checkpoint:** tests/screenshots/oidc-settings/step-08-dark-mode.png
**Maps to:** TBD

## 4. Data Model

### OidcConfig

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | Yes | Primary key |
| issuer_url | String(512) | Yes | OIDC provider issuer URL |
| client_id | String(255) | Yes | OIDC client ID |
| encrypted_client_secret | Text | Yes | Client secret, encrypted at rest (Fernet) |
| provider_name | String(100) | Yes | Display name for the provider (e.g., "PocketId") |
| enabled | Boolean | Yes | Whether OIDC login is active (default: false) |
| hide_local_login | Boolean | Yes | Whether to hide local login form (default: false) |
| scopes | String(255) | No | OIDC scopes to request (default: "openid email profile") |
| configured_by_id | Integer (FK → User.id) | Yes | Admin who last configured OIDC |
| created_at | DateTime | Yes | Record creation timestamp |
| updated_at | DateTime | Yes | Last modification timestamp |

### Relationships

- `OidcConfig.configured_by_id` → `User.id` (many-to-one): Tracks which admin last saved the config.
- Singleton pattern: Only one row should exist. Service layer enforces upsert behavior.
- Shares encryption key with SmtpConfig (`ENCRYPTION_KEY` env var, Fernet).

### Migration Notes

- Remove reliance on `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_PROVIDER_NAME`, `OIDC_HIDE_LOCAL_LOGIN` env vars.
- Add `FORCE_LOCAL_LOGIN` env var (boolean, default false).
- Share `ENCRYPTION_KEY` env var with SMTP feature for Fernet encryption/decryption.

## 5. API Contract

N/A — This feature uses server-rendered HTMX endpoints, not REST API.

### HTMX Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | /settings/auth | Render OIDC config form (secret masked if configured) | Admin only |
| POST | /settings/auth | Create or update OIDC configuration | Admin only |
| POST | /settings/auth/test-discovery | Test OIDC discovery against provided issuer URL | Admin only |

### Modified Endpoints

| Method | Path | Change |
|--------|------|--------|
| GET | /auth/oidc/login | Reads config from DB (`OidcConfig`) instead of env vars |
| GET | /auth/oidc/callback | Reads config from DB (`OidcConfig`) instead of env vars |
| GET | /login | Checks DB config + `FORCE_LOCAL_LOGIN` env var to determine what to show |

## 6. UI Behavior

### Authentication Section (Settings Page, Admin Only)

```
┌─────────────────────────────────────────────────────────┐
│ Authentication                                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Provider Name:  [PocketId                            ]  │
│ Issuer URL:     [https://auth.example.com            ]  │
│ Client ID:      [rsync-viewer                        ]  │
│ Client Secret:  [••••••••                            ]  │
│ Scopes:         [openid email profile                ]  │
│                                                         │
│ [Test Discovery]                                        │
│                                                         │
│ Enable OIDC:        [toggle]                            │
│ Hide Local Login:   [toggle]                            │
│                                                         │
│ ℹ Local login can always be forced via the              │
│   FORCE_LOCAL_LOGIN environment variable as a           │
│   safety fallback.                                      │
│                                                         │
│ [Save]                                                  │
└─────────────────────────────────────────────────────────┘
```

### States

- **Loading:** Spinner while OIDC config is fetched (HTMX swap)
- **Empty:** Form with empty fields, toggles off, helper text: "No OIDC provider configured. Single sign-on is disabled."
- **Configured:** Form pre-filled with saved values, client secret shown as `••••••••`
- **Discovery success:** Green alert below "Test Discovery" button showing discovered endpoints
- **Discovery failure:** Red alert with connection error message (no credentials exposed)
- **Error (validation):** Inline field errors for missing required fields or invalid URL format
- **Success (save):** Toast: "OIDC configuration saved."

### Screenshot Checkpoints

| Step | Description | Path |
|------|-------------|------|
| 1 | Empty OIDC form (no config) | tests/screenshots/oidc-settings/step-01-empty-form.png |
| 2 | Configured with discovery success | tests/screenshots/oidc-settings/step-02-configured.png |
| 3 | Discovery failure | tests/screenshots/oidc-settings/step-03-discovery-failed.png |
| 4 | Non-admin view (section hidden) | tests/screenshots/oidc-settings/step-04-denied.png |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Client secret field left empty on edit | Keep existing encrypted secret; do not overwrite with blank |
| Issuer URL unreachable on discovery test | Show connection error to admin, allow save anyway |
| OIDC disabled while users have active OIDC sessions | Sessions valid until expiry, no new OIDC logins |
| OIDC config deleted or cleared | Treat as "not configured" — local login only |
| `FORCE_LOCAL_LOGIN=true` with "Hide Local Login" on | Local login always shown (env var wins) |
| Admin disables OIDC then re-enables | Config preserved, no re-entry needed |
| Concurrent admin edits | Last-write-wins (singleton upsert) |
| App starts with no `ENCRYPTION_KEY` env var | App refuses to start or logs fatal error (encryption key is required for SMTP and OIDC) |
| Discovery returns unexpected schema | Show generic error: "Discovery response missing required endpoints" |
| Very long issuer URL | Validate max 512 characters, show inline error |
| Dark mode active | All info boxes, badges, and form elements use theme-aware CSS variables. No hardcoded light colors leak through. |
| `--bg-secondary` CSS variable undefined | Info boxes must not fall back to `#f5f5f5`. Either define `--bg-secondary` in both light and dark themes, or use an existing variable like `--table-head-bg`. |

## 8. Dependencies

- **SMTP Email spec (specs/smtp-email.md):** Shares `ENCRYPTION_KEY` env var and Fernet encryption pattern
- **OIDC Authentication spec (specs/oidc-authentication.md):** This spec supersedes AC-009 (env var config). The OIDC login flow, user creation/linking, and session handling remain governed by that spec.
- **M9 Multi-User (complete):** Admin role check, User model
- **`cryptography` (Fernet):** For encrypting client secret at rest (shared dependency with SMTP)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-26 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
| 2026-03-04 | 0.2.0 | finish06 + Claude | AC-016–AC-017, TC-008: Dark mode fix for Callback URL and FORCE_LOCAL_LOGIN info boxes (white boxes on dark background) |
