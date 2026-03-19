# E2E Playwright Tests — Error Scenarios

**Status:** In Progress
**Milestone:** M-GA (GA Maintenance)
**Priority:** High
**Dependencies:** specs/e2e-playwright-happy-path.md (cycle 14 — COMPLETE)

## Feature Description

Add Playwright E2E tests for error and edge-case scenarios across all major UI flows. Tests are added to the existing test files from cycle 14, extending coverage from happy paths to failure modes. This cycle covers authentication failures, CSRF validation, session expiry, RBAC enforcement, and input validation.

## User Story

As a **developer maintaining rsync-viewer**, I want E2E tests that verify error handling and security enforcement so that regressions in auth, CSRF, or RBAC are caught before deployment.

## Acceptance Criteria

### Authentication Errors
- **AC-101:** Invalid password shows error message on login page (no redirect)
- **AC-102:** Non-existent username shows error message on login page
- **AC-103:** Disabled account shows "Account is disabled" error on login

### CSRF Validation
- **AC-110:** Submitting login form with tampered CSRF token is rejected (no login)
- **AC-111:** Submitting registration form with tampered CSRF token is rejected

### Session Expiry / Auth Redirects
- **AC-120:** Accessing `/` with no auth cookie redirects to `/login`
- **AC-121:** Accessing `/settings` with no auth cookie redirects to `/login`
- **AC-122:** Accessing `/admin/users` with no auth cookie redirects to `/login`

### Role-Based Access Control
- **AC-130:** Viewer user accessing `/settings` gets 403 (requires operator+)
- **AC-131:** Viewer user accessing `/admin/users` gets 403 or redirect (requires admin)
- **AC-132:** Viewer user cannot change another user's role via HTMX

### Input Validation
- **AC-140:** Registering with an existing username shows error message
- **AC-141:** Registering with an existing email shows error message
- **AC-142:** Registering with a too-short password shows validation error

## User Test Cases

### TC-101: Invalid Login
1. Navigate to `/login`
2. Enter valid username, wrong password
3. Submit form
4. Verify error message appears
5. Verify still on `/login` (no redirect)

### TC-102: CSRF Tamper
1. Navigate to `/login`
2. Modify the hidden `csrf_token` input value via JS
3. Submit the form
4. Verify login fails (error or redirect back to login)

### TC-103: Session Expiry
1. Clear `access_token` cookie
2. Navigate to `/` (protected page)
3. Verify redirect to `/login`

### TC-104: RBAC — Viewer Denied
1. Log in as viewer user
2. Navigate to `/settings`
3. Verify 403 or access denied message
4. Navigate to `/admin/users`
5. Verify 403 or access denied message

### TC-105: Duplicate Registration
1. Register a user successfully
2. Try to register again with the same username
3. Verify error message about duplicate

### TC-106: Password Validation
1. Navigate to `/register`
2. Enter a 3-character password
3. Submit form
4. Verify validation error

## Backlog (Deferred)
- Real expired JWT testing (craft JWT with past expiry)
- HTMX partial load failures (500 responses from malformed requests)
- Invalid webhook URL format validation
