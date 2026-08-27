# Spec: Security Hardening v2 — Phase 0 Hotfixes

**Version:** 0.1.0
**Created:** 2026-08-27
**PRD Reference:** docs/prd.md
**Status:** SPECCED
**Milestone:** M-GA — GA Maintenance
**Source:** docs/plans/robustness-hardening-plan.md (Phase 0)
**Relationship to v1:** Extends `specs/security-hardening.md` (Feb 2026, complete). One v1 criterion is deliberately superseded: v1 AC-001 "rate limiting per API key" becomes per-client-IP (this spec's AC-003) because the per-key bucket was bypassable with unauthenticated guesses.

## 1. Overview

Close the exploitable authorization, injection, and rate-limiting gaps found in the 2026-08-27 robustness review, and fix the migration drift that leaves the API-key index uncreated in production. Every item is behaviour-preserving for legitimate users; only unauthorized or malformed requests change outcome.

### User Story

As the **homelab operator running rsync-viewer on a reachable network**, I want every API endpoint to enforce authentication and role checks, user-supplied strings to be rendered safely, and brute-force attempts to be throttled per client, so that a stray port exposure or a low-privilege API key cannot read, alter, or script against my sync data.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | `GET /api/v1/analytics/summary`, `/sources`, and `/export` return **401** with no credentials and **200** with a viewer-role JWT or any valid API key. | Must |
| AC-002 | `POST /api/v1/sync-logs` rejects a `source_name` that does not match `^[A-Za-z0-9._-]{1,100}$` with **422**; the analytics source-comparison cards render `source_name` as text, never as markup. | Must |
| AC-003 | Rate limiting is keyed on client IP for all requests; sending N different invalid `X-API-Key` values from one IP exhausts a single bucket and yields **429**. | Must |
| AC-004 | An `X-API-Key` whose 8-char prefix matches no active key triggers `bcrypt.checkpw` only against keys with an empty `key_prefix` (legacy), never against every active key. Successful auth with a legacy key logs a warning recommending rotation. | Must |
| AC-005 | An Alembic revision creates `ix_api_keys_active_prefix (is_active, key_prefix)`; `alembic check` reports no pending model/migration diff, and CI fails when it does. | Must |
| AC-006 | Uvicorn's `--forwarded-allow-ips` is set from the `FORWARDED_ALLOW_IPS` environment variable (default `127.0.0.1`); it is never `*` unless explicitly configured. | Must |
| AC-007 | OIDC login auto-links to an existing local account by email **only** when the ID token claim `email_verified` is `true`; otherwise login is refused with a clear error and no account is created or modified. | Must |
| AC-008 | The effective role of an API key with an owner is `min(role_override, owner.role)`; demoting the owner immediately lowers the key's effective role. | Must |
| AC-009 | Monitors and failures endpoints accept API key **or** JWT; reads require `viewer`, mutations (`POST/PUT/DELETE /monitors`) require `operator`; a viewer-scoped key receives **403** on mutations. | Must |
| AC-010 | `GET /api/v1/webhooks`, `GET /htmx/webhooks`, and `GET /htmx/webhooks/{id}/edit` require `operator`; a viewer receives **403** and never sees webhook `url` or `headers`. | Must |
| AC-011 | Backward cursor pagination on `GET /api/v1/sync-logs` computes `has_next` using the same `source_name`, `start_date`, `end_date`, and synthetic filters as the page query. | Must |

## 3. User Test Cases

### TC-001: Anonymous analytics export
**Precondition:** App running, no credentials.
**Steps:** `curl http://host:8000/api/v1/analytics/export?format=csv`
**Expected Result:** 401 structured error; no data rows.
**Screenshot Checkpoint:** N/A (API)
**Maps to:** AC-001

### TC-002: Malicious source name
**Precondition:** Operator API key.
**Steps:** POST a sync log with `source_name: "<img src=x onerror=alert(1)>"`; open the Analytics tab.
**Expected Result:** 422 validation error; Analytics tab renders no injected element. For a row inserted directly into the DB with markup, the card header shows the literal text.
**Screenshot Checkpoint:** `tests/screenshots/security-hardening-v2/step-01-source-card-escaped.png`
**Maps to:** AC-002

### TC-003: Key brute force
**Precondition:** App running.
**Steps:** Script 100 requests with random `X-API-Key` values from one host.
**Expected Result:** 429 after the configured limit; `Retry-After` header present; server CPU not saturated by bcrypt.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-003, AC-004

### TC-004: Fresh deploy migration
**Precondition:** Empty database.
**Steps:** `alembic upgrade head`, then `alembic check`.
**Expected Result:** Index exists; `alembic check` reports no new operations.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-005

### TC-005: OIDC unverified email
**Precondition:** IdP configured; local admin with email X.
**Steps:** Log in via an IdP that returns `email_verified: false` for email X.
**Expected Result:** Login page shows "email not verified by identity provider"; admin account's `auth_provider`/`oidc_subject` unchanged.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-007

### TC-006: Demoted owner's key
**Precondition:** Admin user with an API key created with `role_override=admin`.
**Steps:** Demote the admin to viewer; call `DELETE /api/v1/monitors/{id}` with the key.
**Expected Result:** 403.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-008, AC-009

### TC-007: Viewer opens webhook edit
**Precondition:** Viewer user logged in.
**Steps:** Request `/htmx/webhooks/{id}/edit`.
**Expected Result:** 403; response body contains no webhook URL.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-010

### TC-008: Filtered backward paging
**Precondition:** 30 logs across two sources and two dates.
**Steps:** Page backward with `source=A&start_date=…` to the first page.
**Expected Result:** `has_next` matches the count of remaining *filtered* rows.
**Screenshot Checkpoint:** N/A
**Maps to:** AC-011

## 4. Data Model

No new tables. One new index:

```
ix_api_keys_active_prefix ON api_keys (is_active, key_prefix)
```

`SyncLogCreate.source_name` gains `pattern=r"^[A-Za-z0-9._-]+$"` and `max_length=100` (column is already `max_length=100`).

## 5. API Contract

No new endpoints. Changed responses:

| Endpoint | Before | After |
|----------|--------|-------|
| `GET /api/v1/analytics/*` | 200 unauthenticated | 401 unauthenticated; 200 viewer+ |
| `POST /api/v1/sync-logs` | 201 for any non-empty `source_name` | 422 for disallowed characters |
| `GET/POST/PUT/DELETE /api/v1/monitors` | API key only, no role check | API key or JWT; viewer read / operator write |
| `GET /api/v1/failures` | API key only | API key or JWT; viewer |
| `GET /api/v1/webhooks` | viewer | operator |
| `GET /htmx/webhooks`, `/htmx/webhooks/{id}/edit` | any logged-in user | operator |
| Any endpoint | per-API-key rate bucket | per-IP rate bucket |

## 6. Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| FORWARDED_ALLOW_IPS | `127.0.0.1` | Comma-separated proxy IPs whose `X-Forwarded-*` headers uvicorn trusts. Set to your reverse proxy's address. |

## 7. Edge Cases

- **Legacy keys (empty `key_prefix`)** cannot be backfilled — only the bcrypt hash is stored. They continue to work via the restricted fallback (AC-004) and are logged for rotation.
- **Dev key (`DEBUG=true` + `DEFAULT_API_KEY`)** continues to bypass lookup and is treated as operator; unchanged.
- **Behind a reverse proxy with `FORWARDED_ALLOW_IPS` unset**, all clients share the proxy's IP and therefore one rate bucket. README must document setting the variable.
- **OIDC `email_verified` absent** is treated as unverified.
- **API key with `role_override` but no `user_id`** (legacy): effective role stays `role_override` (no owner to clamp against).
- **Existing `source_name` rows** that would now fail validation are unaffected (validation is on create); the template fix makes their display safe.
- **`alembic check`** needs a live database in CI; reuse the `docker-compose.dev.yml` test service.

## 8. Screenshot Checkpoints

One UI checkpoint (TC-002): Analytics tab source card showing escaped markup as literal text, saved to `tests/screenshots/security-hardening-v2/step-01-source-card-escaped.png`.
