# Spec: User Management

**Version:** 0.1.0
**Created:** 2026-02-22
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Implement multi-user support with user accounts, authentication, role-based access control, and per-user API key management. Transforms rsync-viewer from a single-key application into a multi-user platform suitable for shared homelab environments.

### User Story

As a homelab administrator sharing rsync-viewer with family or team members, I want user accounts with different permission levels, so that viewers can check sync status without being able to modify configurations or delete data.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Users can register with username, email, and password | Must |
| AC-002 | Passwords are hashed with bcrypt or argon2 before storage | Must |
| AC-003 | Users can log in and receive a JWT access token | Must |
| AC-004 | JWT tokens expire after a configurable period (default: 24 hours) with refresh token support | Must |
| AC-005 | Three roles exist: Admin, Operator, Viewer with distinct permission sets | Must |
| AC-006 | Admin can view, create, edit, delete all resources and manage users | Must |
| AC-007 | Operator can view all resources, create sync logs, manage webhooks, but cannot delete or manage users | Must |
| AC-008 | Viewer can view resources only (read-only access) | Must |
| AC-009 | A login page is available at `/login` with username/password form | Must |
| AC-010 | Protected routes redirect unauthenticated users to `/login` | Must |
| AC-011 | Per-user API keys can be generated, listed, and revoked from user settings | Must |
| AC-012 | API key permissions are scoped to the user's role | Must |
| AC-013 | Password reset flow via email is available | Should |
| AC-014 | OAuth login (GitHub) is supported as an alternative to password auth | Should |
| AC-015 | First registered user is automatically assigned the Admin role | Must |
| AC-016 | Session timeout displays a re-login prompt without losing the current page | Should |

## 3. User Test Cases

### TC-001: User registration and login

**Precondition:** App running, no users exist
**Steps:**
1. Navigate to `/register`
2. Register with username "admin", email "admin@example.com", password "SecurePass123!"
3. Verify redirect to `/login`
4. Log in with the new credentials
**Expected Result:** User is created with Admin role (first user). Login succeeds, JWT token issued, user redirected to dashboard. Dashboard shows username in header.
**Screenshot Checkpoint:** tests/screenshots/user-management/step-01-register.png, tests/screenshots/user-management/step-02-login.png
**Maps to:** AC-001, AC-003, AC-015

### TC-002: Role-based access control

**Precondition:** Admin and Viewer users exist
**Steps:**
1. Log in as Viewer
2. Attempt to access `/settings` (webhook management)
3. Attempt to DELETE a sync log via API
4. Log in as Admin
5. Access `/settings` and delete a sync log
**Expected Result:** Viewer can see the dashboard but gets 403 on settings and delete operations. Admin can perform all actions.
**Screenshot Checkpoint:** tests/screenshots/user-management/step-03-viewer-restricted.png
**Maps to:** AC-005, AC-006, AC-007, AC-008

### TC-003: API key management

**Precondition:** Logged-in user
**Steps:**
1. Navigate to user settings / API keys section
2. Click "Generate New API Key"
3. Copy the displayed key
4. Use the key to authenticate an API request
5. Revoke the key
6. Attempt to use the revoked key
**Expected Result:** Key is generated and shown once. API requests with the key succeed and inherit user's role permissions. After revocation, the key returns 401.
**Screenshot Checkpoint:** tests/screenshots/user-management/step-04-api-keys.png
**Maps to:** AC-011, AC-012

### TC-004: Password reset

**Precondition:** User exists with email configured
**Steps:**
1. Click "Forgot Password" on login page
2. Enter email address
3. Receive reset email (or verify token in logs for testing)
4. Click reset link and set new password
5. Log in with new password
**Expected Result:** Reset token is generated and sent. New password works for login. Old password no longer works. Reset token is single-use.
**Screenshot Checkpoint:** tests/screenshots/user-management/step-05-password-reset.png
**Maps to:** AC-013

### TC-005: Protected routes

**Precondition:** App running, not logged in
**Steps:**
1. Navigate directly to `/` (dashboard)
2. Navigate to `/settings`
3. Call API endpoint without token
**Expected Result:** UI routes redirect to `/login` with a return URL parameter. API returns 401 for unauthenticated requests.
**Screenshot Checkpoint:** tests/screenshots/user-management/step-06-redirect-login.png
**Maps to:** AC-010

## 4. Data Model

### User (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| username | String(50) | Yes | Unique username |
| email | String(255) | Yes | Unique email address |
| password_hash | String(255) | Yes | bcrypt/argon2 hashed password |
| role | String(20) | Yes | "admin", "operator", or "viewer". Default "viewer" |
| is_active | Boolean | Yes | Account enabled. Default true |
| last_login_at | DateTime | No | Last successful login timestamp |
| created_at | DateTime | Yes | Account creation timestamp |
| updated_at | DateTime | Yes | Last modification timestamp |

### RefreshToken (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| user_id | UUID (FK) | Yes | Reference to User |
| token_hash | String(255) | Yes | Hashed refresh token |
| expires_at | DateTime | Yes | Token expiration |
| revoked | Boolean | Yes | Whether token has been revoked. Default false |
| created_at | DateTime | Yes | Token creation timestamp |

### PasswordResetToken (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| user_id | UUID (FK) | Yes | Reference to User |
| token_hash | String(255) | Yes | Hashed reset token |
| expires_at | DateTime | Yes | Token expiration (default: 1 hour) |
| used | Boolean | Yes | Whether token has been used. Default false |
| created_at | DateTime | Yes | Token creation timestamp |

### Modified: ApiKey

| Field | Change | Description |
|-------|--------|-------------|
| user_id | New column (FK) | Reference to User who owns this key |
| role_override | New column | Optional role override (must be <= user's role) |

### Permission Matrix

| Resource | Admin | Operator | Viewer |
|----------|-------|----------|--------|
| View dashboard | Yes | Yes | Yes |
| View sync logs | Yes | Yes | Yes |
| Submit sync logs (API) | Yes | Yes | No |
| View webhooks | Yes | Yes | Yes |
| Manage webhooks | Yes | Yes | No |
| Delete sync logs | Yes | No | No |
| Manage users | Yes | No | No |
| View settings | Yes | Yes | No |
| Manage API keys (own) | Yes | Yes | Yes |
| Manage API keys (others) | Yes | No | No |

### Relationships

- `RefreshToken.user_id` -> `User.id` (FK, cascade delete)
- `PasswordResetToken.user_id` -> `User.id` (FK, cascade delete)
- `ApiKey.user_id` -> `User.id` (FK)
- One User can have many ApiKeys, RefreshTokens, PasswordResetTokens

## 5. API Contract

### POST /api/v1/auth/register

**Description:** Register a new user account.

**Request:**
```json
{
  "username": "admin",
  "email": "admin@example.com",
  "password": "SecurePass123!"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "created_at": "2026-02-22T10:00:00Z"
}
```

**Error Responses:**
- `400` - Invalid input (weak password, invalid email)
- `409` - Username or email already exists

### POST /api/v1/auth/login

**Description:** Authenticate and receive tokens.

**Request:**
```json
{
  "username": "admin",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Error Responses:**
- `401` - Invalid credentials
- `403` - Account disabled

### POST /api/v1/auth/refresh

**Description:** Refresh an expired access token.

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "expires_in": 86400
}
```

### POST /api/v1/auth/password-reset/request

**Description:** Request a password reset email.

**Request:**
```json
{
  "email": "admin@example.com"
}
```

**Response (200):**
```json
{
  "message": "If an account with that email exists, a reset link has been sent."
}
```

### POST /api/v1/auth/password-reset/confirm

**Description:** Reset password with token.

**Request:**
```json
{
  "token": "reset-token-value",
  "new_password": "NewSecurePass456!"
}
```

**Response (200):**
```json
{
  "message": "Password has been reset successfully."
}
```

### GET /api/v1/users (Admin only)

**Description:** List all users.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "is_active": true,
    "last_login_at": "2026-02-22T10:00:00Z",
    "created_at": "2026-02-22T09:00:00Z"
  }
]
```

### PUT /api/v1/users/{id}/role (Admin only)

**Description:** Change a user's role.

**Request:**
```json
{
  "role": "operator"
}
```

**Response (200):** Updated user object.

## 6. UI Behavior

### Login Page (`/login`)

- **Fields:** Username, password, "Remember me" checkbox
- **Actions:** Login button, "Forgot Password" link, "Register" link
- **Error:** Invalid credentials show inline error message
- **Redirect:** After login, redirect to original requested URL or dashboard

### Registration Page (`/register`)

- **Fields:** Username, email, password, confirm password
- **Validation:** Password strength indicator, email format check, username availability
- **Success:** Redirect to login with success message

### User Settings (`/settings/account`)

- **Profile:** Username (read-only), email (editable), role (read-only)
- **Password:** Change password form (current + new + confirm)
- **API Keys:** List of user's keys with prefix, created date, revoke button, generate new button
- **Sessions:** Active sessions list with revoke capability

### Admin User Management (`/admin/users`)

- **List:** Table of all users with username, email, role, status, last login
- **Actions:** Change role dropdown, enable/disable toggle, delete user (with confirmation)
- **Restrictions:** Cannot demote or delete own account

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| First user registration | Automatically gets Admin role |
| Admin tries to demote themselves | Rejected — at least one admin must exist |
| Admin tries to delete themselves | Rejected with error message |
| Expired JWT on UI request | Redirect to login, preserve return URL |
| Expired JWT on API request | Return 401, client should use refresh token |
| Refresh token expired | Return 401, user must re-login |
| Password reset token used twice | Second use rejected with "token already used" error |
| Password reset token expired | Return 400 with "token expired" message |
| OAuth user has no password | Password reset unavailable, must use OAuth login |
| User deleted while logged in | Next API call returns 401, session invalidated |
| Registration disabled by admin | `/register` shows "Registration is currently disabled" |
| Brute force login attempts | Rate limiting via security-hardening spec |

## 8. Dependencies

- python-jose or PyJWT (JWT handling)
- bcrypt or argon2-cffi (password hashing)
- Security hardening spec (rate limiting on auth endpoints)
- Logging spec (audit trail for auth events)
- SMTP configuration (for password reset emails)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-22 | 0.1.0 | finish06 | Initial spec from TODO conversion |
