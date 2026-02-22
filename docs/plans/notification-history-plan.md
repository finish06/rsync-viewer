# Implementation Plan: Notification History

**Spec:** specs/notification-history.md
**Created:** 2026-02-22
**Status:** Approved

## Overview

Add a notification history section to the dashboard that displays webhook delivery attempts from the existing `notification_logs` table, with filtering and pagination.

## Files to Modify

1. **`app/main.py`** — Add `GET /htmx/notifications` route
2. **`app/templates/index.html`** — Add "Notifications" tab to dashboard
3. **`app/static/css/styles.css`** — Add notification-specific styles (status badges)

## Files to Create

1. **`app/templates/partials/notifications_list.html`** — Notification log table partial
2. **`tests/test_notification_history.py`** — Tests for AC-001 through AC-010

## Implementation Steps

### Step 1: HTMX Route (app/main.py)

Add `GET /htmx/notifications` handler that:
- Accepts query params: `status`, `webhook_name`, `source_name`, `offset`, `limit`
- Queries `NotificationLog` with JOINs to `FailureEvent` and `WebhookEndpoint`
- Returns paginated results sorted by `created_at` DESC
- Passes filter options (unique webhook names, source names, statuses) to template

### Step 2: Dashboard Tab (index.html)

Add a "Notifications" tab button that:
- Uses `hx-get="/htmx/notifications"` with `hx-target="#notifications-container"`
- Tab switching hides sync table/charts, shows notification container
- Tab state managed via CSS classes (active/inactive)

### Step 3: Notification List Partial (notifications_list.html)

Table with columns:
- Webhook Name (from WebhookEndpoint.name, or "[deleted]")
- Source (from FailureEvent.source_name)
- Type (from FailureEvent.failure_type)
- Status (badge: green=success, red=failed, gray=skipped)
- HTTP Code
- Attempt #
- Error (truncated, expandable)
- Timestamp (formatted)

Filter row above table with:
- Status dropdown (All/Success/Failed/Skipped)
- Webhook dropdown
- Source dropdown

Pagination below table (same offset/limit pattern as sync_table).

### Step 4: CSS Additions

- `.notification-status-badge` with variants: `.status-success`, `.status-failed`, `.status-skipped`
- `.notification-table` inheriting from `.sync-table` pattern
- Tab styling for dashboard navigation

## Test Strategy

- 10-15 tests covering AC-001 through AC-010
- Use `create_notification_log` fixture that also creates FailureEvent and WebhookEndpoint
- Test empty state, populated state, filtering, pagination, deleted webhook handling
