# Spec: SMTP Email Configuration

**Version:** 0.1.0
**Created:** 2026-02-26
**PRD Reference:** docs/prd.md
**Status:** Draft
**Milestone:** M11 — Polish & Infrastructure

## 1. Overview

Allow the application to send emails to users by configuring an SMTP server. Admins can set up SMTP server details (host, port, credentials, TLS) through a UI in the admin settings section. The system uses this configuration to send transactional emails such as password resets.

### User Story

As an Admin, I want to configure SMTP settings so that the system can send password reset emails to users.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Admin can create SMTP configuration with host, port, username, password, TLS/SSL, from address, and from name | Must |
| AC-002 | Admin can edit an existing SMTP configuration | Must |
| AC-003 | Admin can send a test email to a specified address to verify SMTP config works | Must |
| AC-004 | SMTP credentials are encrypted at rest in the database | Must |
| AC-005 | SMTP credentials are transmitted securely (never in plaintext in responses or logs) | Must |
| AC-006 | Non-admin users cannot access the SMTP settings page or endpoints | Must |
| AC-007 | SMTP password is masked when retrieving saved configuration (displayed as `••••••••`) | Should |
| AC-008 | The system gracefully handles missing SMTP configuration when an email send is attempted (logs warning, does not expose to end user) | Should |
| AC-009 | Only one SMTP configuration exists system-wide (singleton pattern) | Should |
| AC-010 | Connection test failure displays the SMTP error message to the admin | Should |

## 3. User Test Cases

### TC-001: Admin configures SMTP for the first time

**Precondition:** Admin is logged in. No SMTP configuration exists.
**Steps:**
1. Navigate to Settings > Email
2. Fill in SMTP host (`smtp.example.com`), port (`587`), username, password
3. Select "STARTTLS" for encryption
4. Enter from address (`noreply@example.com`) and from name (`Rsync Viewer`)
5. Click "Save"
**Expected Result:** Success toast appears. Form shows saved values with password masked.
**Screenshot Checkpoint:** tests/screenshots/smtp-email/step-01-smtp-configured.png
**Maps to:** TBD

### TC-002: Admin sends a test email

**Precondition:** Admin is logged in. SMTP configuration is saved.
**Steps:**
1. Navigate to Settings > Email
2. Enter a test recipient email address
3. Click "Send Test Email"
**Expected Result:** Success message: "Test email sent successfully." Email arrives at the recipient inbox.
**Screenshot Checkpoint:** tests/screenshots/smtp-email/step-02-test-email-sent.png
**Maps to:** TBD

### TC-003: Admin edits SMTP configuration

**Precondition:** Admin is logged in. SMTP configuration exists.
**Steps:**
1. Navigate to Settings > Email
2. Change the port from `587` to `465`
3. Change encryption to "SSL/TLS"
4. Leave password field empty (keep existing)
5. Click "Save"
**Expected Result:** Configuration updated. Port and encryption reflect new values. Password remains unchanged.
**Screenshot Checkpoint:** tests/screenshots/smtp-email/step-03-smtp-updated.png
**Maps to:** TBD

### TC-004: Test email fails with bad config

**Precondition:** Admin is logged in. SMTP configuration is saved with an invalid host.
**Steps:**
1. Navigate to Settings > Email
2. Enter a test recipient email address
3. Click "Send Test Email"
**Expected Result:** Error message displays the SMTP connection error (e.g., "Connection refused" or "Hostname not found"). No credentials are exposed in the error.
**Screenshot Checkpoint:** tests/screenshots/smtp-email/step-04-test-email-failed.png
**Maps to:** TBD

### TC-005: Non-admin cannot access SMTP settings

**Precondition:** User with Operator or Viewer role is logged in.
**Steps:**
1. Navigate to Settings page
**Expected Result:** SMTP/Email configuration section is not visible. Direct URL access returns 403.
**Screenshot Checkpoint:** tests/screenshots/smtp-email/step-05-non-admin-denied.png
**Maps to:** TBD

## 4. Data Model

### SmtpConfig

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | Yes | Primary key |
| host | String(255) | Yes | SMTP server hostname |
| port | Integer | Yes | SMTP server port (typically 25, 465, or 587) |
| username | String(255) | No | SMTP authentication username |
| encrypted_password | Text | No | SMTP password, encrypted at rest (Fernet symmetric encryption) |
| encryption | Enum("none", "starttls", "ssl_tls") | Yes | Connection encryption method |
| from_address | String(255) | Yes | Sender email address |
| from_name | String(255) | No | Sender display name (default: "Rsync Viewer") |
| enabled | Boolean | Yes | Whether email sending is active (default: true) |
| configured_by_id | Integer (FK → User.id) | Yes | Admin who last configured SMTP |
| created_at | DateTime | Yes | Record creation timestamp |
| updated_at | DateTime | Yes | Last modification timestamp |

### Relationships

- `SmtpConfig.configured_by_id` → `User.id` (many-to-one): Tracks which admin last saved the config.
- Singleton pattern: Only one row should exist. Service layer enforces upsert behavior.

## 5. API Contract

N/A — This feature uses server-rendered HTMX endpoints, not REST API.

### HTMX Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | /settings/email | Render SMTP config form (with masked password if configured) | Admin only |
| POST | /settings/email | Create or update SMTP configuration | Admin only |
| POST | /settings/email/test | Send test email to provided address | Admin only |

## 6. UI Behavior

### States

- **Loading:** Spinner while SMTP config is fetched (HTMX swap)
- **Empty:** Form with empty fields, helper text: "No SMTP server configured. Email features (password reset) are disabled."
- **Configured:** Form pre-filled with saved values, password shown as `••••••••`, "Save" and "Send Test Email" buttons enabled
- **Error (validation):** Inline field errors for missing required fields or invalid port
- **Error (connection test):** Alert banner with SMTP error message (credentials stripped)
- **Success (save):** Toast: "SMTP configuration saved."
- **Success (test):** Toast: "Test email sent successfully to {address}."

### Screenshot Checkpoints

| Step | Description | Path |
|------|-------------|------|
| 1 | Empty SMTP form (no config) | tests/screenshots/smtp-email/step-01-empty-form.png |
| 2 | Filled and saved config | tests/screenshots/smtp-email/step-02-configured.png |
| 3 | Test email success | tests/screenshots/smtp-email/step-03-test-success.png |
| 4 | Test email failure | tests/screenshots/smtp-email/step-04-test-failure.png |
| 5 | Non-admin denied | tests/screenshots/smtp-email/step-05-denied.png |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Password field left empty on edit | Keep existing encrypted password; do not overwrite with blank |
| SMTP host unreachable on test | Show timeout error to admin, do not hang UI (30s timeout) |
| No SMTP config when password reset requested | Log warning, return generic "reset link sent" message to user, do not send email |
| SMTP config exists but `enabled: false` | Same behavior as no config — log and suppress silently |
| Very long SMTP password | Accept up to 1024 characters |
| Port out of valid range | Validate 1–65535, show inline error |
| Special characters in from_name | Properly encode in email headers (RFC 2047) |
| Concurrent admin edits | Last-write-wins (singleton upsert), no conflict resolution needed |
| Encryption key rotation | Document process; re-encrypt password when app starts with new key |

## 8. Dependencies

- **M9 Multi-User (complete):** Admin role check, User model with email addresses
- **Python `smtplib`:** Built-in, no external dependency for sending
- **`cryptography` (Fernet):** For encrypting SMTP password at rest. Add to `requirements.txt`.
- **Environment variable `SMTP_ENCRYPTION_KEY`:** Fernet key for encrypting/decrypting stored password. Must be set in production `.env`.

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-26 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
