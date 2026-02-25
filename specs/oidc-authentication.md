# Spec: OIDC Authentication

**Version:** 0.1.0
**Created:** 2026-02-24
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Add OpenID Connect (OIDC) authentication as an additional login method alongside local username/password auth. Supports a single OIDC provider at a time (e.g., PocketId or any generic OIDC-compliant provider), configured via environment variables. Users who authenticate via OIDC get a local account auto-created or auto-linked by email, with a default Viewer role.

### User Story

As a homelab administrator, I want to authenticate via my existing OIDC provider (PocketId), so that I can use single sign-on across my homelab services without managing separate credentials.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | OIDC login is available when `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, and `OIDC_CLIENT_SECRET` env vars are set | Must |
| AC-002 | Login page shows a provider-branded "Login with {provider_name}" button below the local login form when OIDC is configured | Must |
| AC-003 | Clicking the OIDC button initiates the Authorization Code Flow, redirecting to the provider's authorize endpoint | Must |
| AC-004 | After successful OIDC auth, the callback endpoint exchanges the code for tokens and validates the ID token | Must |
| AC-005 | If no local user exists with the OIDC subject (`sub` claim), a new user is auto-created with Viewer role | Must |
| AC-006 | If a local user exists with a matching email, the OIDC identity is auto-linked to that account | Must |
| AC-007 | OIDC-created users cannot set a local password — they are strictly OIDC-only | Must |
| AC-008 | After OIDC login, a local JWT session is issued (same as local auth) so existing session handling works unchanged | Must |
| AC-009 | OIDC configuration is read from environment variables: `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_PROVIDER_NAME`, `OIDC_HIDE_LOCAL_LOGIN` | Must |
| AC-010 | The app performs OIDC Discovery (fetches `/.well-known/openid-configuration`) to resolve authorize, token, and userinfo endpoints | Must |
| AC-011 | OIDC login requests `openid email profile` scopes | Must |
| AC-012 | When `OIDC_HIDE_LOCAL_LOGIN=true`, the local username/password form is hidden (OIDC-only mode) | Should |
| AC-013 | OIDC state parameter is validated to prevent CSRF attacks on the callback | Must |
| AC-014 | OIDC nonce is validated in the ID token to prevent replay attacks | Must |
| AC-015 | When OIDC env vars are not set, the login page shows only the local login form (no OIDC button) | Must |
| AC-016 | Logging out of rsync-viewer destroys the local session only (no OIDC provider logout) | Must |
| AC-017 | An OIDC-linked user's display name and email are updated from OIDC claims on each login | Should |

## 3. User Test Cases

### TC-001: First-time OIDC login (new user)

**Precondition:** OIDC is configured, no local user exists for the OIDC user
**Steps:**
1. Navigate to `/login`
2. Click "Login with PocketId" button
3. Authenticate at the PocketId login page
4. Approve the consent screen (if shown)
**Expected Result:** User is redirected back to rsync-viewer dashboard. A new local user is created with Viewer role, username derived from OIDC `preferred_username` or `email`, and `auth_provider` set to "oidc". JWT session is active.
**Screenshot Checkpoint:** tests/screenshots/oidc/step-01-login-button.png, tests/screenshots/oidc/step-02-redirect-back.png
**Maps to:** TBD

### TC-002: OIDC login with existing email match

**Precondition:** Local user exists with email "user@example.com", OIDC user has same email
**Steps:**
1. Navigate to `/login`
2. Click "Login with PocketId"
3. Authenticate at PocketId
**Expected Result:** OIDC identity is linked to the existing local account. User is logged in with their existing role (not downgraded to Viewer). The `oidc_subject` field is populated on the user record.
**Screenshot Checkpoint:** tests/screenshots/oidc/step-03-linked-account.png
**Maps to:** TBD

### TC-003: Returning OIDC user login

**Precondition:** User has previously logged in via OIDC (account exists with oidc_subject)
**Steps:**
1. Navigate to `/login`
2. Click "Login with PocketId"
3. Authenticate at PocketId
**Expected Result:** User is logged in immediately. No new account created. `last_login_at` is updated.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-004: OIDC not configured

**Precondition:** OIDC env vars are not set
**Steps:**
1. Navigate to `/login`
**Expected Result:** Only the local username/password form is shown. No OIDC button visible.
**Screenshot Checkpoint:** tests/screenshots/oidc/step-04-no-oidc.png
**Maps to:** TBD

### TC-005: Hide local login mode

**Precondition:** OIDC configured with `OIDC_HIDE_LOCAL_LOGIN=true`
**Steps:**
1. Navigate to `/login`
**Expected Result:** Only the "Login with PocketId" button is shown. No username/password form. Local API auth (JWT/API key) still works for programmatic access.
**Screenshot Checkpoint:** tests/screenshots/oidc/step-05-oidc-only.png
**Maps to:** TBD

### TC-006: OIDC provider unavailable

**Precondition:** OIDC configured but provider is unreachable
**Steps:**
1. Navigate to `/login`
2. Click "Login with PocketId"
**Expected Result:** User sees an error message: "Unable to reach authentication provider. Please try again later." If local login is not hidden, user can fall back to local auth.
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

## 4. Data Model

### Modified: User

| Field | Change | Description |
|-------|--------|-------------|
| auth_provider | New column, String(20) | "local" or "oidc". Default "local" |
| oidc_subject | New column, String(255), nullable, unique | OIDC `sub` claim for identity mapping |
| oidc_issuer | New column, String(512), nullable | OIDC issuer URL for the linked provider |

### OidcState (transient, stored in cache or DB with short TTL)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| state | String(64) | Yes | Random state parameter for CSRF protection |
| nonce | String(64) | Yes | Random nonce for ID token replay protection |
| return_url | String(512) | No | URL to redirect to after login |
| created_at | DateTime | Yes | Expiry reference (valid for 10 minutes) |

### Relationships

- `User.oidc_subject` is unique — one OIDC identity maps to exactly one local user
- No new foreign keys; OIDC fields are added to the existing User model

## 5. API Contract

### GET /auth/oidc/login

**Description:** Initiates the OIDC Authorization Code Flow. Generates state and nonce, stores them, and redirects to the provider's authorize endpoint.

**Query Parameters:**
- `return_url` (optional) — URL to redirect to after login

**Response (302):** Redirect to `{issuer}/authorize?client_id=...&redirect_uri=...&scope=openid+email+profile&response_type=code&state=...&nonce=...`

### GET /auth/oidc/callback

**Description:** Handles the OIDC provider callback. Exchanges authorization code for tokens, validates ID token, creates/links user, issues local JWT session.

**Query Parameters:**
- `code` — Authorization code from provider
- `state` — State parameter for CSRF validation

**Response (302):** Redirect to dashboard or `return_url` with session cookie set.

**Error Responses:**
- `400` — Invalid state, missing code, or token exchange failure
- `502` — OIDC provider unreachable

### GET /api/v1/auth/oidc/config

**Description:** Returns OIDC configuration status (for frontend to know whether to show the button).

**Response (200):**
```json
{
  "enabled": true,
  "provider_name": "PocketId",
  "hide_local_login": false
}
```

## 6. UI Behavior

### Login Page (`/login`)

- **OIDC disabled:** Standard username/password form only
- **OIDC enabled:** Username/password form with a divider ("or") and a "Login with {provider_name}" button below
- **OIDC enabled + hide local login:** Only the "Login with {provider_name}" button, no form
- **Loading:** Button shows spinner after click while redirect initiates
- **Error:** Flash message on callback failure ("Authentication failed. Please try again.")

### Screenshot Checkpoints

| Step | Description | Path |
|------|-------------|------|
| 1 | Login page with OIDC button | tests/screenshots/oidc/step-01-login-button.png |
| 2 | Dashboard after OIDC login | tests/screenshots/oidc/step-02-redirect-back.png |
| 3 | User profile showing linked OIDC | tests/screenshots/oidc/step-03-linked-account.png |
| 4 | Login page without OIDC | tests/screenshots/oidc/step-04-no-oidc.png |
| 5 | OIDC-only login mode | tests/screenshots/oidc/step-05-oidc-only.png |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| OIDC provider returns no email claim | Account creation fails with error; email is required |
| OIDC `sub` already linked to a different local user than email match | `sub` mapping takes precedence — log in as the sub-linked user |
| OIDC user's email changes at provider | Email updated on next login (AC-017) |
| Two OIDC users have the same email | First to authenticate claims the email link; second gets a new account with username from `sub` |
| State parameter expired (user took >10 min) | Callback returns error, user prompted to try again |
| OIDC discovery endpoint unreachable at app startup | App starts without OIDC; logs warning; OIDC button hidden |
| OIDC discovery endpoint unreachable at login time | Error shown to user, local login still available (unless hidden) |
| Admin changes `OIDC_ISSUER_URL` to a different provider | Existing OIDC users can't login until re-linked (different `sub` values) |
| OIDC-only user tries password reset | Rejected with message: "This account uses SSO. Please log in with your identity provider." |

## 8. Dependencies

- `authlib` or `httpx` (OIDC client library for Authorization Code Flow + Discovery)
- User Management spec (specs/user-management.md) — provides User model, JWT session, roles
- Security Hardening spec — rate limiting on auth endpoints
- `.env.example` updated with all new OIDC env vars

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-24 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
