# Implementation Plan: Monitoring Setup Wizard

**Spec Version**: 0.1.0
**Created**: 2026-03-02
**Team Size**: Solo
**Estimated Duration**: 2 days

## Overview

Add a "Monitoring" tab to the Settings page with a guided rsync-client setup wizard (Docker Compose generation + auto-provisioned API key) and the relocated synthetic health check settings. Move the Changelog to its own dedicated settings tab.

## Objectives

- Provide a zero-friction way to deploy rsync-client containers from the Settings UI
- Auto-provision API keys embedded in copyable Docker Compose snippets
- Consolidate monitoring features into a single "Monitoring" tab
- Reduce settings page clutter by giving the Changelog its own tab

## Success Criteria

- All 13 acceptance criteria implemented and tested
- Code coverage >= 80%
- All quality gates passing (ruff, mypy, pytest)
- No regressions in existing settings functionality

## Acceptance Criteria Analysis

### AC-001: Monitoring tab on Settings page
- **Complexity**: Simple
- **Effort**: 1h
- **Tasks**: Restructure `settings.html` to add tab navigation, add Monitoring tab container
- **Dependencies**: None
- **Testing**: Verify tab renders for admin, hidden for non-admin

### AC-002: Two sections in Monitoring tab
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: Create `monitoring_setup.html` partial with two sections
- **Dependencies**: AC-001

### AC-003: Rsync Client Setup form fields
- **Complexity**: Medium
- **Effort**: 1.5h
- **Tasks**: Form HTML with source_name, rsync_source, cron_schedule, ssh_key_path, rsync_args fields + defaults
- **Dependencies**: AC-002

### AC-004: Form validation
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: Server-side validation in POST handler, return partial with inline errors
- **Dependencies**: AC-003

### AC-005: Auto-provision API key
- **Complexity**: Medium
- **Effort**: 1.5h
- **Tasks**: Reuse API key creation pattern from `app/routes/api_keys.py`, name key `rsync-client-{source_name}`, handle duplicate names
- **Dependencies**: AC-003, AC-004

### AC-006: Docker Compose snippet output
- **Complexity**: Medium
- **Effort**: 1.5h
- **Tasks**: Build compose YAML string from form inputs + generated key, render in `<pre><code>` with copy button
- **Dependencies**: AC-005

### AC-007: Hub URL and env vars in snippet
- **Complexity**: Medium
- **Effort**: 1h
- **Tasks**: Parse rsync_source into REMOTE_HOST/USER/PATH, detect hub URL from request (X-Forwarded-* aware)
- **Dependencies**: AC-006

### AC-008: Raw key shown once
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: Snippet is rendered only in the POST response partial; GET re-renders blank form
- **Dependencies**: AC-005, AC-006 (inherent in HTMX partial pattern)

### AC-009: Synthetic Health Check in Monitoring tab
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: Include existing `synthetic_settings.html` partial via HTMX load inside the Monitoring tab
- **Dependencies**: AC-001, AC-002

### AC-010: Changelog moved to own tab
- **Complexity**: Simple
- **Effort**: 45min
- **Tasks**: Add "Changelog" tab to settings, move changelog section out of right column, create changelog tab container with HTMX load
- **Dependencies**: AC-001

### AC-011: HTMX lazy-load for Monitoring tab
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: `hx-get="/htmx/monitoring-setup"` with `hx-trigger="load"` pattern (same as all other settings sections)
- **Dependencies**: AC-001

### AC-012: Push/pull sync mode toggle
- **Complexity**: Simple
- **Effort**: 30min
- **Tasks**: Radio buttons in form, pass to compose generator, adjust volume mount (`:ro` vs `:rw`)
- **Dependencies**: AC-003, AC-006

### AC-013: Instructional text
- **Complexity**: Simple
- **Effort**: 15min
- **Tasks**: Static HTML paragraph explaining rsync client and hub connection
- **Dependencies**: AC-002

## Implementation Phases

### Phase 1: Settings Page Restructure (AC-001, AC-010)

Restructure `settings.html` to use a tab navigation pattern. Move the Changelog to its own tab, add the Monitoring tab placeholder.

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-001 | Add tab navigation to `settings.html` (General, Monitoring, Changelog) | 1h | None | AC-001, AC-010 |
| TASK-002 | Move changelog from right column to Changelog tab with HTMX lazy load | 30min | TASK-001 | AC-010 |
| TASK-003 | Add Monitoring tab container with HTMX lazy load | 15min | TASK-001 | AC-001, AC-011 |
| TASK-004 | Write tests for tab rendering (admin vs non-admin, tab visibility) | 45min | TASK-001 | AC-001, AC-010 |

**Phase Duration**: ~2.5h

### Phase 2: Monitoring Tab Backend (AC-002, AC-003, AC-004, AC-005, AC-009, AC-012, AC-013)

Create the route handlers and compose generation logic.

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-005 | Add `GET /htmx/monitoring-setup` route returning monitoring partial | 30min | TASK-003 | AC-002, AC-011 |
| TASK-006 | Create `monitoring_setup.html` partial: form fields + instructional text + synthetic section include | 1.5h | TASK-005 | AC-002, AC-003, AC-012, AC-013 |
| TASK-007 | Add `POST /htmx/monitoring-setup/generate` route: validate form, parse rsync_source, provision API key | 2h | TASK-005 | AC-004, AC-005 |
| TASK-008 | Implement compose snippet generation: build YAML string from inputs + key + hub URL | 1.5h | TASK-007 | AC-006, AC-007, AC-008 |
| TASK-009 | Create `monitoring_compose_result.html` partial: `<pre><code>` block + copy button | 30min | TASK-008 | AC-006 |
| TASK-010 | Include synthetic settings in monitoring tab via nested HTMX load | 15min | TASK-005 | AC-009 |

**Phase Duration**: ~6h

### Phase 3: Testing (all ACs)

Write tests covering all acceptance criteria and edge cases.

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-011 | Test `GET /htmx/monitoring-setup` renders form with defaults, admin-only | 30min | TASK-006 | AC-001, AC-002, AC-003 |
| TASK-012 | Test `POST generate` happy path: API key created, compose snippet returned with correct env vars | 1h | TASK-008 | AC-005, AC-006, AC-007 |
| TASK-013 | Test validation: missing source_name, missing rsync_source, inline errors | 30min | TASK-007 | AC-004 |
| TASK-014 | Test rsync_source parsing: `user@host:/path` → REMOTE_HOST, REMOTE_USER, REMOTE_PATH | 30min | TASK-007 | AC-007 |
| TASK-015 | Test push/pull mode: volume mount `:ro` vs `:rw`, SYNC_MODE env var | 30min | TASK-008 | AC-012 |
| TASK-016 | Test duplicate source name: numeric suffix on API key name | 30min | TASK-007 | AC-005 (edge case) |
| TASK-017 | Test source name sanitization: spaces/special chars → kebab-case | 15min | TASK-007 | AC-005 (edge case) |
| TASK-018 | Test changelog tab: HTMX endpoint still works, no longer in right column | 30min | TASK-002 | AC-010 |
| TASK-019 | Test hub URL detection: X-Forwarded-Host, X-Forwarded-Proto headers | 30min | TASK-008 | AC-007 (edge case) |

**Phase Duration**: ~5h

### Phase 4: Polish & Verify

| Task ID | Description | Effort | Dependencies | ACs |
|---------|-------------|--------|--------------|-----|
| TASK-020 | CSS styling for tab navigation, form layout, code block | 30min | TASK-006, TASK-009 | All UI |
| TASK-021 | Copy-to-clipboard JS for compose snippet | 15min | TASK-009 | AC-006 |
| TASK-022 | Run full quality gates: ruff, mypy, pytest, coverage | 30min | All | All |
| TASK-023 | Verify no regressions in existing settings (SMTP, OIDC, API keys, webhooks) | 15min | TASK-001 | N/A |

**Phase Duration**: ~1.5h

## Effort Summary

| Phase | Estimated Hours |
|-------|-----------------|
| Phase 1: Settings Restructure | 2.5h |
| Phase 2: Monitoring Tab Backend | 6h |
| Phase 3: Testing | 5h |
| Phase 4: Polish & Verify | 1.5h |
| **Total** | **15h** |

## Critical Implementation Details

### Settings Page Tab Structure

The current `settings.html` uses a two-column grid layout with no tab navigation. This needs to change to a tabbed layout:

```
[General] [Monitoring] [Changelog]
─────────────────────────────────
Tab content area (lazy-loaded via HTMX)
```

**General tab** contains the existing two-column grid (Appearance, API Keys, Webhooks | Auth, SMTP).
**Monitoring tab** contains Rsync Client Setup wizard + Synthetic Health Check.
**Changelog tab** contains the existing changelog content.

Tab switching uses HTMX: clicking a tab sets it as active and loads the content via `hx-get`. The General tab loads by default.

### Rsync Source Parsing

The `rsync_source` field (e.g. `backupuser@192.168.1.100:/data/backups`) is parsed into:
- `REMOTE_USER` = `backupuser`
- `REMOTE_HOST` = `192.168.1.100`
- `REMOTE_PATH` = `/data/backups`

Parsing logic: split on `@` for user, then split on `:` for host and path. Validate format in the POST handler.

### Hub URL Detection

```python
def _detect_hub_url(request: Request) -> str:
    proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
    host = request.headers.get("X-Forwarded-Host", request.headers.get("host", "localhost:8000"))
    return f"{proto}://{host}"
```

### API Key Provisioning

Reuses the exact pattern from `app/routes/api_keys.py:63-127`:
1. Generate `raw_key = "rsv_" + secrets.token_urlsafe(32)`
2. Hash: `key_hash = hash_api_key(raw_key)`
3. Create `ApiKey(name=f"rsync-client-{sanitized_name}", key_hash=..., user_id=...)`
4. Return `raw_key` embedded in the compose snippet

### Duplicate Name Handling

Before creating the API key, check if `rsync-client-{name}` already exists (active keys for this user). If so, append `-2`, `-3`, etc.

### Source Name Sanitization

```python
import re
def _sanitize_source_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")
```

## Dependencies

### Internal Dependencies
- `ApiKey` model + `hash_api_key` utility (exists)
- `synthetic_settings.html` partial (exists, relocated)
- Changelog HTMX route `GET /htmx/changelog` (exists)
- Settings page template `settings.html` (modified)

### No External Dependencies
- No new Python packages
- No database migrations
- No new models

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Tab restructure breaks existing settings sections | Medium | High | Test all existing sections still load after restructure (TASK-023) |
| Rsync source format varies (no `@`, SSH URLs, etc.) | Low | Medium | Validate format, show hint for expected format |
| Copy-to-clipboard JS compatibility | Low | Low | Use `navigator.clipboard.writeText` with fallback |
| Existing tests reference settings page HTML structure | Medium | Medium | Update any tests that assert on settings page DOM |

## Testing Strategy

1. **Unit Tests**: Rsync source parsing, source name sanitization, compose YAML generation, hub URL detection
2. **Integration Tests**: Full POST flow (form → API key created → compose snippet returned), validation errors, admin-only access
3. **Regression Tests**: Existing settings sections still load (SMTP, OIDC, API keys, webhooks, changelog)

## Deliverables

### Code
- `app/routes/settings.py` — New monitoring-setup routes (GET + POST)
- `app/templates/settings.html` — Restructured with tab navigation
- `app/templates/partials/monitoring_setup.html` — Monitoring tab content (form + synthetic section)
- `app/templates/partials/monitoring_compose_result.html` — Generated compose snippet display
- `app/templates/partials/settings_general.html` — Extracted general tab content (existing sections)

### Tests
- `tests/test_monitoring_setup_wizard.py` — All AC tests

### Static Assets
- Tab navigation CSS (in existing `settings.css` or `styles.css`)
- Copy-to-clipboard JS (in `app/static/js/`)

## File Change Summary

| File | Action | Description |
|------|--------|-------------|
| `app/templates/settings.html` | Modify | Add tab nav, extract general content, add Monitoring + Changelog tabs |
| `app/templates/partials/settings_general.html` | Create | Extracted general settings content (two-column grid) |
| `app/templates/partials/monitoring_setup.html` | Create | Monitoring tab: rsync client form + synthetic health check |
| `app/templates/partials/monitoring_compose_result.html` | Create | Compose snippet code block with copy button |
| `app/routes/settings.py` | Modify | Add GET/POST monitoring-setup routes |
| `app/static/css/styles.css` | Modify | Tab navigation styles |
| `app/static/js/monitoring.js` | Create | Copy-to-clipboard for compose snippet |
| `tests/test_monitoring_setup_wizard.py` | Create | All acceptance criteria tests |

## Plan History

- 2026-03-02: Initial plan created
