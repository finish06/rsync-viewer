# Spec: Webhook Notification Service

**Version:** 0.1.0
**Created:** 2026-02-21
**PRD Reference:** docs/prd.md
**Status:** Draft
**Milestone:** M2 — Notifications

## 1. Overview

Generic webhook dispatch service that sends HTTP POST notifications to configured endpoint URLs whenever a FailureEvent is created. Supports retry with exponential backoff, auto-disable on repeated failures, and a settings page UI for managing webhook endpoints.

### User Story

As a homelab administrator, I want to configure webhook URLs that receive notifications when syncs fail or go stale, so that I can integrate with any alerting tool (Home Assistant, Discord, Slack, custom scripts) without modifying the application.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | When a FailureEvent is created, all enabled webhook endpoints receive an HTTP POST with a JSON payload describing the failure | Must |
| AC-002 | CRUD API endpoints exist for webhook endpoints at `/api/v1/webhooks` | Must |
| AC-003 | Webhook payload includes source_name, failure_type, details, detected_at, and sync_log_id (if applicable) | Must |
| AC-004 | Failed webhook deliveries are retried up to 3 times with exponential backoff (30s, 60s, 120s) | Must |
| AC-005 | Each delivery attempt is logged in a NotificationLog table with status, HTTP status code, and error message | Must |
| AC-006 | Webhook endpoints are automatically disabled after 10 consecutive failures | Must |
| AC-007 | A settings page UI at `/settings` allows users to add, edit, enable/disable, and delete webhook endpoints | Must |
| AC-008 | Webhook requests include configurable custom headers (e.g., Authorization tokens) | Should |
| AC-009 | After successful webhook delivery, the FailureEvent's `notified` field is set to true | Must |
| AC-010 | Webhook dispatch is synchronous (triggered inline when FailureEvent is created, not via background scheduler) | Must |
| AC-011 | Disabled webhooks are skipped during dispatch without error | Must |

## 3. User Test Cases

### TC-001: Webhook fires on sync failure

**Precondition:** App is running, one webhook endpoint configured and enabled
**Steps:**
1. Submit a sync log via POST `/api/v1/sync-logs` with `exit_code: 1`
2. Check the NotificationLog for the delivery record
**Expected Result:** Webhook endpoint receives POST with JSON payload containing failure details. NotificationLog shows status "success" with HTTP 200. FailureEvent.notified is true.
**Screenshot Checkpoint:** N/A (backend-only)
**Maps to:** TBD

### TC-002: Webhook retry on failure

**Precondition:** App is running, one webhook endpoint configured pointing to an unreachable URL
**Steps:**
1. Submit a sync log with `exit_code: 1`
2. Check NotificationLog entries
**Expected Result:** 3 delivery attempts logged with increasing delays. All show status "failed". FailureEvent.notified remains false. Webhook consecutive_failures incremented.
**Screenshot Checkpoint:** N/A (backend-only)
**Maps to:** TBD

### TC-003: Auto-disable after consecutive failures

**Precondition:** Webhook endpoint has 9 consecutive failures
**Steps:**
1. Trigger one more failed delivery (10th consecutive)
2. Check webhook endpoint status
**Expected Result:** Webhook endpoint's `enabled` field is set to false. No further deliveries attempted to this endpoint.
**Screenshot Checkpoint:** N/A (backend-only)
**Maps to:** TBD

### TC-004: Manage webhooks via settings UI

**Precondition:** App is running, user navigates to `/settings`
**Steps:**
1. Navigate to webhook management section on settings page
2. Add a new webhook: name "Discord Alert", URL "https://discord.com/api/webhooks/...", enabled
3. Save the webhook
4. Verify it appears in the webhook list
**Expected Result:** Webhook is created and displayed in the settings page webhook list with name, URL (masked), and enabled status.
**Screenshot Checkpoint:** tests/screenshots/webhook-service/step-04-settings-webhook-list.png
**Maps to:** TBD

### TC-005: Manage webhooks via API

**Precondition:** App is running, API key configured
**Steps:**
1. POST `/api/v1/webhooks` with `{"name": "Test Hook", "url": "https://example.com/hook", "enabled": true}`
2. GET `/api/v1/webhooks`
3. PUT `/api/v1/webhooks/{id}` with `{"enabled": false}`
4. DELETE `/api/v1/webhooks/{id}`
**Expected Result:** Full CRUD lifecycle works. Webhook appears in list after creation, updates correctly, and is removed after deletion.
**Screenshot Checkpoint:** N/A (API-only)
**Maps to:** TBD

## 4. Data Model

### WebhookEndpoint (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| name | String(100) | Yes | Human-readable name for the webhook |
| url | String(2048) | Yes | Target URL for HTTP POST delivery |
| headers | JSON | No | Custom headers to include in requests (e.g., {"Authorization": "Bearer xyz"}) |
| enabled | Boolean | Yes | Whether this endpoint receives notifications. Default true |
| consecutive_failures | Integer | Yes | Count of consecutive failed deliveries. Reset to 0 on success. Default 0 |
| created_at | DateTime | Yes | Record creation timestamp |
| updated_at | DateTime | Yes | Last modification timestamp |

### NotificationLog (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| failure_event_id | UUID (FK) | Yes | Reference to the FailureEvent that triggered this notification |
| webhook_endpoint_id | UUID (FK) | Yes | Reference to the target webhook endpoint |
| status | String(20) | Yes | "success", "failed", or "skipped" |
| http_status_code | Integer | No | HTTP response status code (null if connection failed) |
| error_message | String | No | Error details if delivery failed |
| attempt_number | Integer | Yes | Which attempt this was (1, 2, or 3) |
| created_at | DateTime | Yes | When this delivery attempt was made |

### Relationships

- `NotificationLog.failure_event_id` -> `FailureEvent.id` (FK)
- `NotificationLog.webhook_endpoint_id` -> `WebhookEndpoint.id` (FK)
- One FailureEvent can have many NotificationLogs (one per endpoint per attempt)

## 5. API Contract

### GET /api/v1/webhooks

**Description:** List all webhook endpoints.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "Discord Alert",
    "url": "https://discord.com/api/webhooks/...",
    "headers": {"Authorization": "Bearer xyz"},
    "enabled": true,
    "consecutive_failures": 0,
    "created_at": "2026-02-21T08:00:00Z",
    "updated_at": "2026-02-21T08:00:00Z"
  }
]
```

**Error Responses:**
- `401` - Missing or invalid API key

### POST /api/v1/webhooks

**Description:** Create a new webhook endpoint.

**Request:**
```json
{
  "name": "Discord Alert",
  "url": "https://discord.com/api/webhooks/...",
  "headers": {"Authorization": "Bearer xyz"},
  "enabled": true
}
```

**Response (201):** Created webhook object.

**Error Responses:**
- `400` - Invalid input (missing name or URL, invalid URL format)
- `401` - Missing or invalid API key

### PUT /api/v1/webhooks/{id}

**Description:** Update an existing webhook endpoint.

**Request:**
```json
{
  "name": "Updated Name",
  "url": "https://new-url.com/hook",
  "headers": {},
  "enabled": false
}
```

**Response (200):** Updated webhook object.

**Error Responses:**
- `400` - Invalid input
- `401` - Missing or invalid API key
- `404` - Webhook not found

### DELETE /api/v1/webhooks/{id}

**Description:** Delete a webhook endpoint.

**Response (204):** No content.

**Error Responses:**
- `401` - Missing or invalid API key
- `404` - Webhook not found

### Webhook Payload (outgoing POST to configured URLs)

**Description:** JSON payload sent to each enabled webhook endpoint when a FailureEvent is created.

```json
{
  "event": "failure_detected",
  "source_name": "backup-server",
  "failure_type": "exit_code",
  "details": "rsync exited with code 23",
  "detected_at": "2026-02-21T12:00:00Z",
  "sync_log_id": "uuid-or-null",
  "failure_event_id": "uuid"
}
```

## 6. UI Behavior

### Settings Page — Webhook Management Section

- **Loading:** Spinner while webhooks load via HTMX
- **Empty:** "No webhook endpoints configured. Add one to receive failure notifications."
- **Success:** Table of webhooks with columns: Name, URL (truncated/masked), Enabled toggle, Consecutive Failures count, Edit/Delete actions
- **Error:** Toast notification with error message
- **Add Form:** Modal or inline form with fields: Name, URL, Custom Headers (JSON textarea), Enabled checkbox
- **Edit:** Same form pre-populated with existing values
- **Delete:** Confirmation dialog before deletion

### Screenshot Checkpoints

| Step | Description | Path |
|------|-------------|------|
| 1 | Empty webhook list state | tests/screenshots/webhook-service/step-01-empty-list.png |
| 2 | Add webhook form | tests/screenshots/webhook-service/step-02-add-form.png |
| 3 | Webhook list with entries | tests/screenshots/webhook-service/step-03-webhook-list.png |
| 4 | Edit webhook form | tests/screenshots/webhook-service/step-04-edit-form.png |

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Webhook URL is unreachable | Log failed attempt, retry up to 3 times, increment consecutive_failures |
| Webhook returns non-2xx status | Treat as failure, log HTTP status code, retry |
| Webhook returns 2xx | Treat as success, reset consecutive_failures to 0, mark FailureEvent notified |
| No webhook endpoints configured | FailureEvent created normally, notified stays false, no errors |
| All webhook endpoints disabled | Same as no endpoints — silent skip |
| Webhook endpoint deleted while delivery in progress | Complete current delivery attempt, skip further retries |
| Multiple FailureEvents created rapidly | Each triggers independent webhook dispatch |
| Webhook URL has invalid format | Reject at creation time with 400 error |
| Custom headers contain sensitive data | Store as-is in DB; UI masks header values on display |
| 10th consecutive failure auto-disables | Endpoint disabled, logged, subsequent events skip this endpoint |
| Manual re-enable after auto-disable | Reset consecutive_failures to 0, endpoint active again |

## 8. Dependencies

- FailureEvent model from failure-detection spec (must be implemented first)
- httpx library for async HTTP POST delivery
- Existing settings page at `/settings` (extend with webhook management section)
- HTMX for dynamic UI updates on the settings page

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-21 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
