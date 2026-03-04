# Spec: Monitoring Setup Wizard

**Version:** 0.1.0
**Created:** 2026-03-02
**PRD Reference:** docs/prd.md
**Status:** Complete

## 1. Overview

A new "Monitoring" tab on the Settings page that provides a guided wizard for setting up two monitoring capabilities: (1) deploying rsync-client containers that perform real rsync transfers and report to the hub, and (2) configuring the built-in synthetic health check. The rsync client wizard auto-generates a dedicated API key and renders a ready-to-use Docker Compose service snippet. Additionally, the Changelog is moved to its own dedicated settings tab.

### User Story

As a homelab administrator, I want a guided setup wizard in the settings page that generates a Docker Compose snippet for deploying rsync-client containers — complete with an auto-provisioned API key — so that I can quickly add new sync sources without manually assembling configuration files.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | A new "Monitoring" tab appears on the Settings page (alongside existing tabs/sections), accessible to admin users | Must |
| AC-002 | The Monitoring tab contains two sections: "Rsync Client Setup" and "Synthetic Health Check" | Must |
| AC-003 | The Rsync Client Setup section presents a form with fields: Source Name (required), Rsync Source (required, e.g. `user@host:/path`), Cron Schedule (default `0 */6 * * *`), SSH Key Path (default `~/.ssh/id_rsa`), and Rsync Extra Options (optional, default `-avz --stats`) | Must |
| AC-004 | Clicking "Generate Compose" validates required fields (Source Name, Rsync Source) and shows inline validation errors for empty required fields | Must |
| AC-005 | On valid submission, a new API key is auto-provisioned in the database with name `rsync-client-{source_name}`, tied to the current user, and the raw key is embedded in the generated Docker Compose snippet | Must |
| AC-006 | The generated Docker Compose snippet is a complete `services:` block for the rsync-client image, pre-filled with the user's inputs and the auto-generated API key, displayed in a copyable code block | Must |
| AC-007 | The snippet uses the hub's current URL (derived from the request) as `RSYNC_VIEWER_URL` and includes all required environment variables (`REMOTE_HOST`, `REMOTE_USER`, `REMOTE_PATH`, `RSYNC_VIEWER_API_KEY`, `RSYNC_SOURCE_NAME`, `CRON_SCHEDULE`, `RSYNC_ARGS`) | Must |
| AC-008 | The raw API key is shown only once in the generated snippet; navigating away and returning does not re-display it (consistent with existing API key UX) | Must |
| AC-009 | The Synthetic Health Check section displays the existing enable/disable toggle, interval configuration, and last check result — same as the current `synthetic_settings.html` partial, relocated into the new Monitoring tab | Must |
| AC-010 | The Changelog section is moved from the right column of the settings page to its own dedicated "Changelog" tab | Must |
| AC-011 | The HTMX partial for the Monitoring tab lazy-loads via `hx-get="/htmx/monitoring-setup"` with `hx-trigger="load"` | Should |
| AC-012 | The compose snippet supports both `pull` and `push` sync modes, selectable via a toggle/radio in the form (default: `pull`) | Should |
| AC-013 | The form includes brief instructional text explaining what the rsync client does and how it connects to the hub | Should |

## 3. User Test Cases

### TC-001: Happy path — generate rsync client compose snippet

**Precondition:** Logged in as admin, on Settings page
**Steps:**
1. Click the "Monitoring" tab
2. In the "Rsync Client Setup" section, fill in Source Name: `my-backup-server`
3. Fill in Rsync Source: `backupuser@192.168.1.100:/data/backups`
4. Leave Cron Schedule at default (`0 */6 * * *`)
5. Leave SSH Key Path at default (`~/.ssh/id_rsa`)
6. Optionally add Rsync Extra Options: `-avz --stats --delete`
7. Click "Generate Compose"
**Expected Result:** A Docker Compose service snippet appears in a code block with the source name, rsync source, generated API key, hub URL, and all other fields pre-filled. A new API key named `rsync-client-my-backup-server` appears in the API Keys section.
**Screenshot Checkpoint:** tests/screenshots/monitoring-wizard/step-01-compose-generated.png
**Maps to:** TBD

### TC-002: Validation — missing required fields

**Precondition:** Logged in as admin, on Monitoring tab
**Steps:**
1. Leave Source Name empty
2. Fill in Rsync Source: `user@host:/path`
3. Click "Generate Compose"
**Expected Result:** Inline validation error appears next to Source Name field. No API key is created. No compose snippet is generated.
**Screenshot Checkpoint:** tests/screenshots/monitoring-wizard/step-02-validation-error.png
**Maps to:** TBD

### TC-003: Synthetic health check section visible

**Precondition:** Logged in as admin, on Monitoring tab
**Steps:**
1. Click the "Monitoring" tab
2. Scroll to "Synthetic Health Check" section
**Expected Result:** The enable/disable toggle, interval input, and last check status are displayed (same data as before, now in the Monitoring tab).
**Screenshot Checkpoint:** tests/screenshots/monitoring-wizard/step-03-synthetic-section.png
**Maps to:** TBD

### TC-004: Changelog moved to own tab

**Precondition:** Logged in as admin, on Settings page
**Steps:**
1. Verify "Changelog" appears as a separate tab
2. Click the "Changelog" tab
3. Verify changelog content loads
**Expected Result:** Changelog is no longer in the right column of the main settings page. It has its own dedicated tab with the same content.
**Screenshot Checkpoint:** tests/screenshots/monitoring-wizard/step-04-changelog-tab.png
**Maps to:** TBD

### TC-005: Sync mode toggle — push vs pull

**Precondition:** Logged in as admin, on Monitoring tab
**Steps:**
1. Fill in the rsync client form with valid data
2. Select "Push" sync mode
3. Click "Generate Compose"
**Expected Result:** The generated snippet includes `SYNC_MODE=push` and mounts the data volume as `ro` (read-only). Selecting "Pull" would show `SYNC_MODE=pull` with `rw` mount.
**Screenshot Checkpoint:** tests/screenshots/monitoring-wizard/step-05-push-mode.png
**Maps to:** TBD

## 4. Data Model

No new database entities required. The wizard uses the existing `ApiKey` model to provision keys.

### Existing Entities Used

| Entity | Usage |
|--------|-------|
| `ApiKey` | Auto-provisioned with `name=rsync-client-{source_name}`, `user_id=current_user.id`, `is_active=True` |

## 5. API Contract

### POST /htmx/monitoring-setup/generate

**Description:** Generates a Docker Compose snippet for an rsync-client container and auto-provisions an API key.

**Request (form data):**
| Field | Type | Required | Default |
|-------|------|----------|---------|
| `source_name` | string | Yes | — |
| `rsync_source` | string | Yes | — |
| `cron_schedule` | string | No | `0 */6 * * *` |
| `ssh_key_path` | string | No | `~/.ssh/id_rsa` |
| `rsync_args` | string | No | `-avz --stats` |
| `sync_mode` | string | No | `pull` |

**Response (200):** HTMX partial containing the generated Docker Compose snippet in a `<pre><code>` block with a copy button.

**Error Responses:**
- `422` — Validation error (missing required fields), returned as HTMX partial with inline errors

### GET /htmx/monitoring-setup

**Description:** Renders the Monitoring tab content (rsync client form + synthetic health check section).

**Response (200):** HTMX partial with both sections.

### GET /htmx/changelog

**Description:** Renders the Changelog tab content (moved from inline settings section).

**Response (200):** HTMX partial with changelog content.

## 6. UI Behavior

### States

- **Loading:** "Loading monitoring setup..." placeholder text in the Monitoring tab container
- **Empty (form):** Form fields at defaults, no compose snippet visible, instructional text visible
- **Success:** Compose snippet code block visible below the form with copy button, success toast "API key created and Compose snippet generated"
- **Error:** Inline validation errors next to the offending form fields; DB error shows error toast

### Docker Compose Output Format

The generated snippet follows this structure:

```yaml
# Rsync Client — {source_name}
# Generated by Rsync Log Viewer on {date}
# Add this to your docker-compose.yml

services:
  rsync-client-{source_name}:
    image: ghcr.io/finish06/rsync-client:latest
    container_name: rsync-{source_name}
    restart: unless-stopped
    environment:
      - REMOTE_HOST={parsed_host}
      - REMOTE_USER={parsed_user}
      - REMOTE_PATH={parsed_path}
      - RSYNC_VIEWER_URL={hub_url}
      - RSYNC_VIEWER_API_KEY={raw_api_key}
      - RSYNC_SOURCE_NAME={source_name}
      - CRON_SCHEDULE={cron_schedule}
      - RSYNC_ARGS={rsync_args}
      - SYNC_MODE={sync_mode}
    volumes:
      - {ssh_key_path}:/home/rsync/.ssh/id_rsa:ro
      - ./data:/data:{ro_or_rw}
```

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Source name contains spaces/special chars | Sanitize to kebab-case for container name and API key name |
| Rsync source missing `@` or `:` | Show validation hint: "Expected format: user@host:/path" |
| Duplicate source name API key | Append a numeric suffix: `rsync-client-myserver-2` |
| User generates snippet but never deploys | Orphaned API key remains; user can delete from API Keys tab |
| Non-admin user accesses Monitoring tab | Tab is hidden; direct URL access returns 403 |
| Hub URL detection behind reverse proxy | Use `X-Forwarded-Host` / `X-Forwarded-Proto` headers if present, fall back to request host |

## 8. Dependencies

- Existing `ApiKey` model and `hash_api_key` utility (from M9)
- Existing `synthetic_settings.html` partial (relocated, not rewritten)
- Existing HTMX settings page tab/section pattern
- `examples/rsync-client/` image available at `ghcr.io/finish06/rsync-client:latest` (or built locally)

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-03-02 | 0.1.0 | finish06 + Claude | Initial spec from /add:spec interview |
