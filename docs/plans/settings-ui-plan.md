# Implementation Plan: Settings in the Insight UI (M17)

**Spec:** specs/settings-ui.md · **UX:** specs/ux/settings-ui-ux.md (DRAFT)
**Date:** 2026-08-29
**Maturity:** GA — TDD per task, one PR per cycle, CI green before merge, CHANGELOG promoted in-PR.

## Cycles

| Cycle | Branch | Scope | ACs |
|-------|--------|-------|-----|
| **S1** | `feature/settings-api` | Settings JSON API (SMTP, OIDC, synthetic, monitoring wizard), changelog API, CSRF for cookie-authenticated API mutations, csrf cookie on SPA shell | AC-001–AC-010 |
| **S2** | `feature/spa-settings` | `/app/settings/*` sections, role-aware sub-nav, forms, toasts, unit tests | AC-011–AC-019 |
| **S3** | `feature/settings-cutover` | Redirects, removal of HTMX routes/templates/tests, E2E rewrite, screenshots | AC-020–AC-022 |

## S1 tasks

- **T1 CSRF (AC-010)** — RED: cookie-only `POST /api/v1/webhooks` without header → 403; with header → 201; `X-API-Key` without CSRF → 201; GET never checked. GREEN: extend `CsrfMiddleware` — for `/api/` mutating requests, if no `X-API-Key`/`Authorization` header and an `access_token` cookie exists, validate `X-CSRF-Token`. The SPA shell response sets `csrf_token` if missing. Frontend client attaches the header on non-GET.
- **T2 SMTP API (AC-001–003)** — `app/schemas/settings.py` (`SmtpSettingsRead/Write`, `SmtpTestRequest`), `app/api/endpoints/settings.py`; reuse `get_smtp_config`, `encrypt_password`, `send_test_email_async`.
- **T3 OIDC API (AC-004–006)** — `OidcSettingsRead/Write`, discovery via `fetch_discovery`; callback URL from `request.base_url`.
- **T4 Synthetic API (AC-007)** — read = DB config + in-process state; write = `save_db_config` + start/stop.
- **T5 Monitoring wizard API (AC-008)** — move `_sanitize_source_name`, `_parse_rsync_source`, `_unique_key_name`, `_generate_compose_snippet` into `app/services/monitoring_setup.py` (shared with the HTMX route until S3 removes it).
- **T6 Changelog API (AC-009)** — `app/api/endpoints/changelog.py` using `parse_changelog`.

Tests: `tests/test_settings_api.py`, `tests/test_csrf_api.py`.

## S2 tasks

- **T7 Settings shell** — `features/settings/SettingsLayout.tsx` (sub-nav, role filter from `currentUser()`), routes `/app/settings/:section`, default `api-keys`; `components/Toast.tsx`; `api/client.ts` CSRF header + `mutateJson`.
- **T8 API keys section** — hooks `useApiKeys/useCreateApiKey/useRevokeApiKey`; reveal-once panel; admin "all users".
- **T9 Webhooks section** — list/toggle/test/delete + inline create/edit form with Discord options; JSON headers editor with validation.
- **T10 Email + Sign-in sections** — forms driven by `GET`, `PUT`; test-email and test-discovery actions; encryption-key notice.
- **T11 Monitoring section** — synthetic toggle/interval; wizard → snippet + copy; invalidates liveness/api-keys queries.
- **T12 Users section** — table + actions; last-admin errors inline.
- **T13 Changelog section** — accordion from `/changelog`.

Tests: Vitest per section against MSW handlers (extend `test/handlers.ts` with settings endpoints); coverage ≥ 80 %.

## S3 tasks

- **T14 Redirects + removal (AC-020, AC-021)** — `pages.py`: `/settings` → `/app/settings`, `/admin/users` → `/app/settings/users`; delete `routes/settings.py` (keep nothing), `routes/admin.py`, `routes/api_keys.py`, `routes/webhooks.py`, templates `settings.html`, `admin_users.html`, partials (`api_key*`, `webhook*`, `smtp_settings`, `oidc_settings`, `synthetic_settings`, `synthetic_history`, `monitoring_setup`, `monitoring_compose_result`, `admin_user_list`, `changelog_*`); `base.html` nav → `/app/settings`; drop `CSRF_PROTECTED_PREFIXES` for `/htmx/*` that no longer exist; unit tests for removed routes deleted, remaining assertions updated.
- **T15 E2E (AC-022)** — rewrite `tests/e2e/test_settings.py`, `test_api_keys_e2e.py`, `test_webhooks_e2e.py`, `test_admin_users_e2e.py`, `test_changelog_playwright.py`; screenshots.

## Risks
| Risk | Mitigation |
|---|---|
| CSRF change breaks external cookie-based scripts | Only cookie-authenticated mutations are affected; API keys/Bearer unchanged; documented in CHANGELOG |
| Wizard hub URL behind proxy | reuse `_detect_hub_url` semantics; documented `FORWARDED_ALLOW_IPS` |
| Large E2E churn | stable `data-testid`s from S2; rewrite file-by-file with the local stack |
