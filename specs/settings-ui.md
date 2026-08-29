# Spec: Settings in the Insight UI

**Version:** 0.1.0
**Created:** 2026-08-29
**PRD Reference:** docs/prd.md §6 M17
**Status:** SPECCED
**Milestone:** M17 — Settings in the SPA
**UX artifact:** specs/ux/settings-ui-ux.md
**Plan:** docs/plans/settings-ui-plan.md
**Depends on:** specs/insight-ui.md (M16, shipped v2.12.0)

## 1. Overview

After M16 the dashboard is a React SPA but every administrative screen — API keys, webhooks, email (SMTP), sign-in (OIDC), synthetic monitoring, the monitoring-setup wizard, user management, and the changelog — is still a Jinja2/HTMX page under `/settings` and `/admin/users`. This feature moves them into the SPA at `/app/settings/*` so the product has one UI, one navigation model, and one auth/CSRF story, and retires the HTMX settings routes and templates.

Settings stay a **secondary destination** (M16 principle 4): reached from the ⚙ menu, not the primary nav.

### User Story

As an **operator or admin** of rsync-viewer, I want to manage keys, webhooks, email, sign-in, monitoring, and users from the same interface I use to watch syncs, so that configuration is fast, consistent, and does not throw me into a different-looking page.

## 2. Acceptance Criteria

### Backend — JSON APIs for HTMX-only settings

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | `GET /api/v1/settings/smtp` (admin) returns `{configured, host, port, username, encryption, from_address, from_name, enabled, has_password, encryption_key_configured, updated_at}`; the password is never returned. | Must |
| AC-002 | `PUT /api/v1/settings/smtp` (admin) validates host/port (1–65535)/from_address/encryption ∈ {none, starttls, ssl_tls}; `password` is optional and only replaces the stored secret when non-empty; returns **409** when no encryption key is configured. | Must |
| AC-003 | `POST /api/v1/settings/smtp/test` (admin) with `{to_address}` sends a test email; returns `{sent: true}` or a 4xx/502 with a message that does not leak server internals. | Must |
| AC-004 | `GET /api/v1/settings/oidc` (admin) returns `{configured, issuer_url, client_id, provider_name, scopes, enabled, hide_local_login, has_client_secret, callback_url, encryption_key_configured, updated_at}`; the client secret is never returned. | Must |
| AC-005 | `PUT /api/v1/settings/oidc` (admin) validates required fields; `client_secret` is required on first configuration and optional afterwards; returns 409 without an encryption key. | Must |
| AC-006 | `POST /api/v1/settings/oidc/test-discovery` (admin) with `{issuer_url}` returns the discovered `authorization_endpoint`, `token_endpoint`, `userinfo_endpoint`, `jwks_uri` or a 400 with the failure reason. | Must |
| AC-007 | `GET /api/v1/settings/synthetic` (admin) returns `{enabled, interval_seconds, last_status, last_check_at, last_latency_ms, last_error}`; `PUT` with `{enabled, interval_seconds ≥ 30}` persists and starts/stops the background task immediately. | Must |
| AC-008 | `POST /api/v1/settings/monitoring-setup` (admin) with `{source_name, rsync_source, cron_schedule?, ssh_key_path?, rsync_args?, sync_mode?}` validates `user@host:/path`, provisions an API key named `rsync-client-<source>` (unique suffix), and returns `{snippet, key_name, source_name, api_key}` — the key is shown once. | Must |
| AC-009 | `GET /api/v1/changelog` (any authenticated user) returns the parsed CHANGELOG versions `[{version, date, sections}]` (Unreleased excluded) plus `app_version`; `?all=false` (default) returns the 5 newest. | Must |
| AC-010 | Cookie-authenticated **mutating** requests to `/api/v1/*` must carry a valid `X-CSRF-Token` (double-submit against the `csrf_token` cookie); requests authenticated by `X-API-Key` or `Authorization: Bearer` are exempt. Missing/invalid token → 403 `CSRF_VALIDATION_FAILED`. | Must |

### Frontend — `/app/settings`

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-011 | `/app/settings` shows a sub-navigation: API keys · Webhooks · Email · Sign-in · Monitoring · Users · Changelog. Operators see API keys, Webhooks, Changelog; admins see all. Viewers see API keys and Changelog only. The active section is in the URL (`/app/settings/webhooks`). | Must |
| AC-012 | **API keys**: list own keys (admins can toggle "all users"), create with name + optional role override (≤ own role), copy-once reveal of the new key, revoke with confirmation. | Must |
| AC-013 | **Webhooks**: list with type badge, enabled toggle, consecutive-failure count; create/edit form (name, URL, type generic/discord, headers JSON, source filters, Discord options colour/username/avatar/footer); test button reporting the HTTP result; delete with confirmation. | Must |
| AC-014 | **Email**: SMTP form (host, port, username, password [placeholder "unchanged" when set], encryption, from address/name), save, "send test email" with an address input; shows a clear notice when `ENCRYPTION_KEY` is not configured. | Must |
| AC-015 | **Sign-in**: OIDC form (issuer URL, client ID, client secret [required first time], provider name, scopes, enabled, hide local login), callback URL shown for copy, "test discovery" listing the discovered endpoints. | Must |
| AC-016 | **Monitoring**: synthetic-check toggle + interval with current status; monitoring-setup wizard (source name, rsync source, schedule, SSH key path, args, mode) that returns the compose snippet with a copy button and the one-time key. | Must |
| AC-017 | **Users** (admin): table with username, email, role, status, last login; change role, enable/disable, delete, send password reset — each with confirmation; the last admin cannot be demoted/deleted (server error surfaced inline). | Must |
| AC-018 | **Changelog**: accordion of versions (5 newest, "show older"), current version badge. | Must |
| AC-019 | All mutations send `X-CSRF-Token`; server validation errors render inline next to the form; success shows a transient toast. | Must |

### Cut-over

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-020 | `/settings` → 302 `/app/settings`; `/settings#changelog` → `/app/settings/changelog`; `/admin/users` → `/app/settings/users`; `/notifications` stays server-rendered. | Must |
| AC-021 | HTMX settings/admin/api-key/webhook routes, their templates, `settings.html`, `admin_users.html`, and their HTMX-only tests are removed; the Jinja base nav points to `/app/settings`. | Must |
| AC-022 | Playwright E2E for settings, API keys, webhooks, admin users, and changelog rewritten against the SPA; screenshots under `tests/screenshots/settings-ui/`. | Must |

## 3. User Test Cases

- **TC-001** Operator creates an API key at `/app/settings/api-keys`, sees it once, copies it, revokes it → list updates without reload.
- **TC-002** Admin creates a Discord webhook with a colour, tests it (mock URL → 502 message shown), toggles it off.
- **TC-003** Admin saves SMTP settings without a password change → `has_password` stays true; sends a test email to an invalid host → inline error, no stack trace.
- **TC-004** Admin configures OIDC for the first time without a secret → inline "Client secret is required"; with secret → saved; test discovery against a bogus issuer → inline failure.
- **TC-005** Admin enables synthetic monitoring at 60 s → liveness pill turns from "off" to UP within one interval.
- **TC-006** Admin runs the monitoring wizard → snippet contains the new key; the key appears under API keys as `rsync-client-<source>`.
- **TC-007** Admin demotes the only other admin → allowed; tries to demote themselves → inline "Cannot change your own role".
- **TC-008** Viewer opens `/app/settings` → sees only API keys and Changelog; direct `/app/settings/users` shows "not permitted".
- **TC-009** Legacy links `/settings`, `/admin/users` redirect (TC screenshot `step-01-settings-home`).

## 4. Data Model

No schema changes. Secrets (`encrypted_password`, `encrypted_client_secret`) never leave the server.

## 5. API Contract

New router `app/api/endpoints/settings.py` (prefix `/settings`, admin via router-level dependency except where noted) with schemas in `app/schemas/settings.py`; `app/api/endpoints/changelog.py` (viewer+). Existing routers reused: `/api-keys`, `/webhooks`, `/users`, `/synthetic/*`.

## 6. Edge Cases

- No encryption key → SMTP/OIDC `GET` still works (`configured` may be true) but `PUT` returns 409 with a message naming `ENCRYPTION_KEY`.
- OIDC `enabled=true` with `hide_local_login=true` and `FORCE_LOCAL_LOGIN` unset could lock out local admins — the UI shows a warning; the API allows it (existing behaviour).
- Synthetic interval < 30 is clamped to 30 (existing behaviour) and echoed back.
- Monitoring wizard hub URL is derived from the request (`X-Forwarded-*` when trusted).
- CSRF: the SPA reads the `csrf_token` cookie (non-httpOnly by design); if absent (cookie cleared) the client fetches `/login` is *not* needed — the server sets the cookie on the SPA shell response as well.
- Users with API-key-only access are unaffected by AC-010.

## 7. Screenshot Checkpoints

`tests/screenshots/settings-ui/`: step-01-settings-home, step-02-api-key-created, step-03-webhook-form, step-04-email, step-05-signin, step-06-monitoring-wizard, step-07-users.

## 8. Out of Scope

Login/register/password-reset pages (public, stay Jinja); the `/notifications` page (moves in a later cycle with SSE); monitor CRUD UI (M12).
