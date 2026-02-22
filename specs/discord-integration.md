# Spec: Discord Integration

**Version:** 0.1.0
**Created:** 2026-02-21
**PRD Reference:** docs/prd.md
**Status:** Draft

## 1. Overview

Format failure notifications as rich Discord embeds with color-coded severity, structured fields, and dashboard links. Extends the existing webhook service with Discord-specific payload formatting, user-configurable embed options, and per-source filtering. Uses a generic `webhook_options` table with JSONB to store type-specific configuration, keeping the schema extensible for future integrations.

### User Story

As a homelab admin, I want rsync failure alerts sent as rich Discord embeds, so that I can quickly see failure details at a glance in my Discord server without clicking through to the dashboard.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | When a webhook has `webhook_type="discord"`, the dispatcher formats the payload as a Discord embed (using Discord's webhook execute format with `embeds` array) | Must |
| AC-002 | Discord embeds include structured fields: source name, failure type, details, and detected_at timestamp | Must |
| AC-003 | Discord embeds include a configurable color (from webhook options), defaulting to red (#ff0000) for failures | Must |
| AC-004 | Discord embeds include a link back to the dashboard/failure event | Must |
| AC-005 | Users can configure Discord-specific options (color, username, avatar_url, footer text) stored in the `webhook_options` table as JSONB | Must |
| AC-006 | Users can set `source_filters` on a webhook endpoint to restrict which rsync sources trigger notifications (null = all sources) | Must |
| AC-007 | The dispatcher skips webhooks where `source_filters` is set and the failure event's source_name is not in the list | Must |
| AC-008 | Discord webhook URLs are validated on creation (must match `https://discord.com/api/webhooks/...` or `https://discordapp.com/api/webhooks/...`) | Must |
| AC-009 | A test message endpoint sends a sample Discord embed to verify the webhook is configured correctly | Should |
| AC-010 | The dispatcher respects Discord rate limits — if a 429 response is received, it waits for the `Retry-After` duration before retrying | Must |
| AC-011 | Generic webhooks (`webhook_type="generic"`) continue to work unchanged with the existing payload format | Must |
| AC-012 | The `WebhookEndpoint` model gains `webhook_type` (string, default "generic") and `source_filters` (JSONB, nullable) fields | Must |
| AC-013 | A new `WebhookOptions` model stores type-specific configuration as JSONB, linked one-to-one to `WebhookEndpoint` | Must |

## 3. User Test Cases

### TC-001: Configure Discord Webhook and Receive Failure Alert

**Precondition:** App running, API key available, Discord server with webhook URL created
**Steps:**
1. POST to `/api/v1/webhooks` with `webhook_type: "discord"`, Discord webhook URL, and options (color, username)
2. Submit a sync log with a non-zero exit code for a matching source
3. Check Discord channel for the notification
**Expected Result:** A rich embed appears in Discord with red color, source name, failure type, details, timestamp, and dashboard link
**Screenshot Checkpoint:** N/A (external service)
**Maps to:** TBD

### TC-002: Source Filter Prevents Notification

**Precondition:** Discord webhook configured with `source_filters: ["server-a"]`
**Steps:**
1. Submit a sync log with non-zero exit code from source "server-b"
2. Check Discord channel
**Expected Result:** No notification sent to Discord — source "server-b" is not in the filter list
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-003: Invalid Discord URL Rejected

**Precondition:** App running, API key available
**Steps:**
1. POST to `/api/v1/webhooks` with `webhook_type: "discord"` and URL `https://example.com/not-discord`
2. Observe response
**Expected Result:** 422 validation error indicating the URL is not a valid Discord webhook URL
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-004: Test Message Sent Successfully

**Precondition:** Discord webhook configured and valid
**Steps:**
1. POST to `/api/v1/webhooks/{id}/test`
2. Check Discord channel
**Expected Result:** A test embed appears in Discord with a "Test notification" message and success color
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

### TC-005: Rate Limited Response Handled

**Precondition:** Discord webhook configured, Discord returning 429
**Steps:**
1. Trigger a failure event
2. Discord returns 429 with `Retry-After: 5`
3. Dispatcher waits 5 seconds and retries
**Expected Result:** Message is delivered on retry after the rate limit window passes
**Screenshot Checkpoint:** N/A
**Maps to:** TBD

## 4. Data Model

### WebhookEndpoint (modified)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| webhook_type | VARCHAR(20) | Yes (default "generic") | Type of webhook: "generic" or "discord" |
| source_filters | JSONB | No | List of source names to filter on; null = all sources |

### WebhookOptions (new)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| webhook_endpoint_id | UUID FK | Yes | One-to-one FK to webhook_endpoints |
| options | JSONB | Yes | Type-specific configuration blob |
| created_at | DATETIME | Yes | Record creation timestamp |
| updated_at | DATETIME | Yes | Last modification timestamp |

#### Discord Options Schema (stored in `options` JSONB)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| color | integer | 16711680 (0xff0000, red) | Embed sidebar color as decimal integer |
| username | string | "Rsync Viewer" | Bot display name in Discord |
| avatar_url | string | null | Bot avatar URL |
| footer | string | null | Embed footer text |

### Relationships

- `WebhookOptions` → `WebhookEndpoint`: one-to-one via `webhook_endpoint_id` FK
- `WebhookEndpoint.source_filters` filters against `FailureEvent.source_name`

## 5. API Contract

### POST /api/v1/webhooks (modified)

**Description:** Create a webhook endpoint — now accepts `webhook_type`, `source_filters`, and `options`

**Request:**
```json
{
  "name": "my-discord-alerts",
  "url": "https://discord.com/api/webhooks/1234/abcd",
  "webhook_type": "discord",
  "source_filters": ["backup-server", "nas-sync"],
  "options": {
    "color": 16711680,
    "username": "Rsync Bot",
    "avatar_url": "https://example.com/bot.png",
    "footer": "Rsync Viewer Alerts"
  }
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "name": "my-discord-alerts",
  "url": "https://discord.com/api/webhooks/1234/abcd",
  "webhook_type": "discord",
  "source_filters": ["backup-server", "nas-sync"],
  "options": {
    "color": 16711680,
    "username": "Rsync Bot",
    "avatar_url": "https://example.com/bot.png",
    "footer": "Rsync Viewer Alerts"
  },
  "enabled": true,
  "consecutive_failures": 0,
  "created_at": "2026-02-21T00:00:00Z"
}
```

**Error Responses:**
- `401` — API key missing or invalid
- `422` — Validation error (invalid Discord URL, invalid options)

### POST /api/v1/webhooks/{webhook_id}/test

**Description:** Send a test notification to verify webhook configuration

**Request:** No body required

**Response (200):**
```json
{
  "status": "sent",
  "message": "Test notification sent successfully"
}
```

**Error Responses:**
- `401` — API key missing or invalid
- `404` — Webhook not found
- `502` — Delivery failed (Discord returned error)

## 6. UI Behavior (if applicable)

N/A for this spec — UI for webhook management is covered by AC-007 in specs/webhook-service.md.

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Invalid Discord webhook URL | Reject with 422 validation error on create/update |
| Discord returns 429 (rate limited) | Respect `Retry-After` header, wait specified duration before retry |
| Discord returns 4xx/5xx (non-429) | Follow existing retry logic (3 attempts, exponential backoff) |
| Discord webhook deleted on Discord side | Delivery fails, logged in NotificationLog, auto-disable after 10 failures |
| source_filters contains a source that doesn't exist yet | Allow it — source may be created later |
| Embed color is not a valid integer | Reject with 422 on create/update |
| webhook_type is "generic" with options set | Options are ignored during dispatch (only read for matching type) |
| webhook_type is "discord" with no options | Use defaults (red color, "Rsync Viewer" username) |
| Failure event has no sync_log_id | Dashboard link field omitted from embed |

## 8. Dependencies

- Existing webhook service (specs/webhook-service.md) — must be implemented first
- Discord webhook API (no auth token needed, just HTTP POST to webhook URL)
- No new Python libraries required — standard httpx POST with JSON body

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-21 | 0.1.0 | finish06 | Initial spec from /add:spec interview |
