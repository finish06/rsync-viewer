# E2E Playwright Tests — Happy Paths

**Status:** In Progress
**Milestone:** M-GA (GA Maintenance)
**Priority:** High
**Dependencies:** None (all features already implemented)

## Feature Description

Add comprehensive Playwright browser E2E tests covering all major UI pages and flows. Tests run against a local instance (`docker-compose up -d`) and verify that the full request→render→interaction pipeline works for each page. This cycle covers happy paths only; error scenarios follow in a subsequent cycle.

## User Story

As a **developer maintaining rsync-viewer**, I want a comprehensive Playwright E2E test suite so that I can refactor or extend any feature with confidence that the UI still works end-to-end.

## Acceptance Criteria

### Infrastructure
- **AC-001:** Shared Playwright conftest with reusable fixtures (authenticated browser context, test user creation via API, base URL config)
- **AC-002:** Each test file is self-contained — creates its own test data via API calls in fixtures
- **AC-003:** Tests run against a local instance at `http://localhost:8000` (configurable via `E2E_BASE_URL` env var)
- **AC-004:** All tests use unique usernames/data (UUID-based) to avoid collisions on repeated runs

### Page Coverage
- **AC-010:** Login page — navigate to `/login`, submit valid credentials, verify redirect to dashboard
- **AC-011:** Registration page — navigate to `/register`, create new user, verify redirect to login
- **AC-012:** Dashboard page — authenticated user sees sync table, charts panel, analytics summary loaded via HTMX
- **AC-013:** Analytics page — navigate to `/analytics`, verify charts and source stats render
- **AC-014:** Settings page — navigate to `/settings`, verify SMTP, OIDC, and synthetic monitoring tabs render
- **AC-015:** API Keys page — create a new API key, verify it appears in the list, revoke it, verify removal
- **AC-016:** Webhooks page — create a webhook, verify it appears in list, toggle enable/disable, delete it
- **AC-017:** Admin user management — admin user navigates to `/admin/users`, sees user list, changes a user's role
- **AC-018:** Password reset — navigate to forgot password page, submit email, verify confirmation message
- **AC-019:** Changelog page — navigate to changelog, verify versions render (existing test coverage, ensure parity)

### HTMX Interactions
- **AC-020:** Dashboard HTMX partials load correctly (sync table, charts, notifications)
- **AC-021:** Settings tabs switch content via HTMX without full page reload
- **AC-022:** API key and webhook CRUD operations update the DOM via HTMX responses

### Test Quality
- **AC-030:** All tests pass in a clean environment with `docker-compose up -d`
- **AC-031:** Tests complete in under 3 minutes total
- **AC-032:** No test depends on another test's state (fully independent)

## User Test Cases

### TC-001: Full Login Flow
1. Navigate to `/login`
2. Enter valid username and password
3. Click submit
4. Verify redirect to `/` (dashboard)
5. Verify username appears in the page header/nav

### TC-002: User Registration
1. Navigate to `/register`
2. Fill in username, email, password
3. Submit form
4. Verify redirect to `/login` with success message

### TC-003: Dashboard Data Display
1. Log in as authenticated user
2. Ingest a sync log via API (POST /api/v1/sync-logs)
3. Navigate to `/`
4. Verify sync table contains the ingested log
5. Verify charts panel renders

### TC-004: API Key Lifecycle
1. Log in as authenticated user
2. Navigate to settings, API keys tab
3. Create a new API key with a name
4. Verify the key appears in the list
5. Revoke the key
6. Verify it disappears from the list

### TC-005: Webhook Lifecycle
1. Log in as authenticated user
2. Navigate to settings, webhooks tab
3. Create a webhook (name + URL)
4. Verify it appears in the list
5. Toggle it disabled
6. Delete it
7. Verify removal

### TC-006: Admin User Management
1. Log in as admin user
2. Navigate to `/admin/users`
3. Verify user list renders
4. Change another user's role
5. Verify role update reflected in the list

### TC-007: Settings Tabs
1. Log in as admin user
2. Navigate to `/settings`
3. Click SMTP tab — verify SMTP form renders
4. Click Auth/OIDC tab — verify OIDC form renders
5. Click Synthetic tab — verify synthetic monitoring controls render

### TC-008: Password Reset Request
1. Navigate to `/forgot-password`
2. Enter email address
3. Submit form
4. Verify confirmation message displays

## Data Model

No new models — tests use existing models via API calls.

## Edge Cases (Deferred to Next Cycle)

- Invalid credentials / failed login
- CSRF validation failures
- Session expiry and auth redirects
- Role-based access denial (viewer accessing admin)
- HTMX partial load failures (500 responses)
- Concurrent test data conflicts
