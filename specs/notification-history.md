# Spec: Notification History Dashboard

**Version:** 0.1.0
**Created:** 2026-02-22
**PRD Reference:** docs/prd.md — M2: Notifications
**Status:** Complete
**Milestone:** M2 — Notifications

## 1. Overview

A notification history view in the dashboard that shows webhook delivery attempts with filtering and pagination. The `notification_logs` table already exists and is populated by the webhook dispatcher — this feature surfaces that data to users.

### User Story

As a homelab admin, I want to see a history of webhook notification deliveries, so that I can verify alerts were sent and troubleshoot failed deliveries.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | The dashboard page has a "Notifications" tab/section that loads notification history via HTMX | Must |
| AC-002 | The notification list shows: webhook name, source name, failure type, status (success/failed/skipped), HTTP status code, attempt number, and timestamp | Must |
| AC-003 | The list is paginated (20 per page) with next/previous navigation | Must |
| AC-004 | Users can filter by status (all/success/failed/skipped) | Must |
| AC-005 | Users can filter by webhook endpoint name | Should |
| AC-006 | Users can filter by source name | Should |
| AC-007 | Empty state shows a helpful "No notifications yet" message | Must |
| AC-008 | Failed deliveries display the error message inline or on hover | Should |
| AC-009 | The list is sorted by created_at descending (newest first) | Must |
| AC-010 | The notification count badge shows on the Notifications tab header | Nice |

## 3. User Test Cases

### TC-001: View Notification History

**Precondition:** At least one failure event has triggered webhook dispatch.
**Steps:**
1. Navigate to the dashboard
2. Click the "Notifications" tab
3. See a table of notification delivery attempts
**Expected:** Table shows webhook name, source, status badge, HTTP code, attempt number, timestamp.

### TC-002: Filter by Status

**Precondition:** Mix of successful and failed notifications exist.
**Steps:**
1. View notification history
2. Select "Failed" from the status filter
**Expected:** Only failed notification attempts are shown.

### TC-003: Empty State

**Precondition:** No notification logs exist.
**Steps:**
1. Navigate to dashboard
2. Click "Notifications" tab
**Expected:** Message "No notifications yet" with explanation that notifications appear when webhook deliveries occur.

### TC-004: Pagination

**Precondition:** More than 20 notification logs exist.
**Steps:**
1. View notification history
2. Click "Next" button
**Expected:** Next 20 entries load, "Previous" button appears.

## 4. Data Model

Already exists — no new models needed.

### NotificationLog (existing)
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| failure_event_id | UUID | FK to failure_events |
| webhook_endpoint_id | UUID | FK to webhook_endpoints |
| status | str(20) | "success", "failed", "skipped" |
| http_status_code | int? | HTTP response code |
| error_message | str? | Error details on failure |
| attempt_number | int | 1-3 (retry attempts) |
| created_at | datetime | Timestamp |

### Related lookups needed
- `FailureEvent.source_name` — to show which source triggered the notification
- `FailureEvent.failure_type` — to show "exit_code" or "stale"
- `WebhookEndpoint.name` — to show human-readable webhook name

## 5. HTMX Routes

| Route | Method | Purpose |
|-------|--------|---------|
| GET /htmx/notifications | GET | Load notification history partial with filters + pagination |

## 6. Template Partials

- `partials/notifications_list.html` — Table of notification logs with filters and pagination

## 7. Edge Cases

- Webhook endpoint deleted but notification logs remain → show "[deleted]" for webhook name
- Failure event source name changes → logs retain the source_name at time of notification
- Very long error messages → truncate with tooltip or expandable row
- Concurrent retry attempts → show attempt_number clearly to distinguish retries
