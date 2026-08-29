# Robustness Hardening Plan — Security, Maintainability, Standards

**Date:** 2026-08-27
**Branch reviewed:** `feature/performance-optimization` (HEAD `4b4403b`)
**Scope:** `app/`, `tests/`, `alembic/`, `Dockerfile`, `entrypoint.sh`, `docker-compose*.yml`, `.github/workflows/`, tooling config
**Method:** three parallel read-only reviews (security, maintainability, standards); every finding below was confirmed in source by the orchestrator before inclusion.

---

## 0. Executive summary

The codebase is in good shape for a homelab GA product: credential storage, JWT/cookie hygiene, refresh-token rotation, open-redirect guarding, Jinja autoescape with zero `|safe`, N+1 avoidance, structured logging, and a weekly `pip-audit` are all already done and should not be redone.

The plan addresses four classes of debt, in priority order:

1. **Three exploitable security gaps** (unauthenticated analytics API, stored XSS via `source_name`, rate-limit bypass + bcrypt amplification on API-key auth) plus a **migration drift bug on the current branch** (the perf commit's index is never created in production). These are one-day fixes and go first.
2. **Defense-in-depth gaps** typical of a project that grew fast: SSRF on webhook URLs, allowlist-style CSRF, sessions not revoked on password reset, proxy headers trusted from anywhere, root container with test deps baked in.
3. **Quality gates that exist on paper only.** The GA rules (complexity ≤10, file ≤300 lines, function ≤50 lines, docstrings, secrets scan, lockfile) are not enforced by any tool; `ruff` runs with default rules only and `mypy` has package-wide error suppression. Current violations: 5 complexity, 10 files, 35 functions.
4. **Structural duplication:** every feature is implemented twice (REST + HTMX) with business logic in handlers, so the two halves have drifted (three auth patterns, validation differences, a pagination bug). A service layer exists in three places and should be applied everywhere.

Recommended sequencing: **Phase 0 → 1 → 2 → 3**. Phase 2's blocking lint rules must not be switched on until Phase 3's refactors land, or CI will go red on 50 pre-existing violations.

---

## Phase 0 — Hotfixes (ship as individual `fix:` PRs this week)

Each item is small, isolated, and testable. Covered by `specs/security-hardening-v2.md` (AC-001…AC-011) and `docs/plans/security-hardening-plan.md`; the v1 spec `specs/security-hardening.md` is complete and untouched.

| # | Finding | Location | Fix | Test |
|---|---------|----------|-----|------|
| 0.1 | **Analytics API is unauthenticated.** `/api/v1/analytics/{summary,sources,export}` declare only `SessionDep`; `/api/` is exempt from `AuthRedirectMiddleware`. Anyone reaching the port can export 10k rows. | `app/api/endpoints/analytics.py:46,133,200`; `app/middleware.py:149` | Add `Depends(require_role_or_api_key(ROLE_VIEWER))` to all three (same pattern as `sync_logs.py:172`). Better: put it as a router-level dependency. | 401 without creds; 200 with viewer key. |
| 0.2 | **Stored XSS via `source_name`.** Analytics source cards build HTML by string concat and assign `innerHTML`; schema only enforces `min_length`. Operator key → script in every admin's browser; `csrf_token` cookie is readable by JS by design, so the script can drive admin HTMX actions. | `app/templates/partials/analytics.html:278`; `app/schemas/sync_log.py:10-15`; dead copy at `app/templates/analytics.html:151-165` | Render cards with `createElement`/`textContent`. Add `pattern=r"^[A-Za-z0-9._-]+$", max_length=100` to `SyncLogCreate.source_name`. Delete the unused template copy. | POST with `<img onerror>` name → 422; existing rendering test asserts escaped output. |
| 0.3 | **Rate-limit bypass + bcrypt amplification.** Limiter keys on the raw `X-API-Key` header, so every guessed key gets a fresh bucket. Unknown prefix → full scan of all active keys with `bcrypt.checkpw` on each. | `app/rate_limit.py:14-16`; `app/api/deps.py:55-59` | Key the limiter on client IP (use API key identity only for post-auth quotas if needed). Remove the legacy full-scan fallback: backfill `key_prefix` in a migration, then treat "no prefix match" as invalid. | Repeated bad keys from one IP hit 429; no-prefix-match returns 401 without bcrypt calls (assert via mock). |
| 0.4 | **Migration drift on this branch.** `ix_api_keys_active_prefix` was added to the model in `4b4403b` but no Alembic revision creates it; lifespan does not run `create_all`. Production never gets the index the perf PR advertises. | `app/models/sync_log.py:41`; `alembic/versions/` (4 revisions, none mention it) | Add a revision creating the index (and the `key_prefix` backfill from 0.3). Add an `alembic check` step to CI so autogenerate diffs fail the build. | CI job. |
| 0.5 | **Proxy headers trusted from any IP.** `--forwarded-allow-ips "*"` lets any client spoof `X-Forwarded-For/Proto/Host`, defeating IP rate limiting, poisoning `client_ip` logs, and altering the OIDC `redirect_uri` derived from `request.base_url`. | `Dockerfile:20`; `app/routes/auth.py:136,176`; `app/routes/settings.py:493-499` | Make it `FORWARDED_ALLOW_IPS` env (default: docker bridge / proxy CIDR). Document in README. | Manual smoke. |
| 0.6 | **OIDC auto-links accounts by unverified email.** Any IdP-asserted `email` matching a local user (including admin) takes over that account. | `app/services/oidc.py:294-304` | Require `claims.get("email_verified") is True` before auto-link; otherwise create a new user or reject. Then **merge PR #35** (signature verification) — do not redo that work. | Unit test with `email_verified: false`. |
| 0.7 | **API-key `role_override` survives owner demotion.** Override is checked ≤ owner role only at creation. | `app/api/deps.py:357-358` | Effective role = `min(role_override, user.role)`. | Demote user → key loses admin. |
| 0.8 | **Monitors/failures ignore RBAC and reject JWT.** They use `ApiKeyDep`, which never checks role and cannot accept a browser session. A viewer-scoped key can delete monitors. | `app/api/endpoints/monitors.py:22,35,74,106`; `failures.py:22-24` | Switch to `require_role_or_api_key(ROLE_OPERATOR)` for mutations, `ROLE_VIEWER` for reads. Deprecate `ApiKeyDep`. | Viewer key → 403 on DELETE. |
| 0.9 | **Webhook secrets visible to viewers.** `GET /api/v1/webhooks` (viewer) returns full `url` and `headers`; `/htmx/webhooks` list and edit have no role check. | `app/api/endpoints/webhooks.py:58-61`; `app/routes/webhooks.py:52-57,177-195` | Require `ROLE_OPERATOR` on those routes; redact `headers` and mask URL path in list responses. | Viewer → 403 / redacted. |
| 0.10 | **Cursor pagination `has_next` probe drops filters.** Backward-page probe rebuilds the query with only `source_name`; `start_date`, `end_date`, synthetic filter are silently dropped, so `has_next`/`next_cursor` are wrong when set. | `app/api/endpoints/sync_logs.py:305-330` | Build the filtered base statement once; derive page query and probe from it. | Regression test with date filter + backward cursor. |

**Exit criteria:** all ten merged to `main`; `specs/security-hardening.md` ACs each have a passing test; PR #35 merged.

---

## Phase 1 — Security defense-in-depth (next cycle, ~1 week)

Spec: extend `specs/security-hardening.md` or open `specs/security-hardening-2.md`.

### 1.1 Request-level protections
- **CSRF deny-by-default.** Replace the `/htmx/*` prefix allowlist with "every non-`/api/` mutating request must carry a valid token" (with an explicit exempt list for `/login`, `/register` if needed). Set `secure=not debug` on the `csrf_token` cookie. (`app/middleware.py:192-226`; cookie sets in `pages.py:114,135,197,213`, `routes/auth.py:74,89,250,274`.) Note cookie-authenticated `/api/v1` mutations currently rely on `SameSite=Lax` alone — acceptable, but document it or require `X-CSRF-Token` when auth came from a cookie.
- **SSRF guard for outbound URLs.** Webhook URLs (any scheme/host accepted; test endpoints echo status/error text — a port scanner for the docker network) and OIDC `issuer_url` discovery. Validate scheme ∈ {http, https}, resolve host, reject loopback/RFC1918/link-local, re-check at send time. (`app/schemas/webhook.py:17`; `app/routes/webhooks.py:107-118,372-383`; `app/api/endpoints/webhooks.py:229-241`; `app/routes/settings.py:440`.)
- **Body-size middleware:** wrap `int(content_length)` (non-numeric header → 500 today); note chunked bodies bypass it — rely on reverse-proxy limit and document. (`app/middleware.py:127`)
- **Timing-safe login:** compare against a dummy bcrypt hash when the user does not exist; return the generic reset message for SSO accounts. (`app/api/endpoints/auth.py:91-95,261-264`; `app/routes/auth.py:56-60`)

### 1.2 Session lifecycle
- On password reset/change and admin disable: revoke the user's `RefreshToken` rows. Add a `token_version` (or `password_changed_at`) claim check in `get_current_user` so 24-hour access tokens die too. Consider shortening `jwt_access_expiry_minutes` now that refresh tokens exist. (`app/api/endpoints/auth.py:329-336`; `users.py:200-207`; `config.py:27`)
- Move the password-reset token out of the GET query string (POST body or fragment) **and** run uvicorn with `--no-access-log` — `RequestLoggingMiddleware` already logs path-only, but uvicorn's default access log (the `get_uvicorn_log_config` in `logging_config.py:62` is never wired) prints path+query. (`app/routes/pages.py:201-205`; `Dockerfile:20`)
- Registration: default `registration_enabled` to false once any user exists, or set `REGISTRATION_ENABLED=false` in `docker-compose.prod.yml` and README. (`config.py:31`)

### 1.3 Browser hardening
- Vendor `htmx` and `chart.js` into `app/static/` (removes unpinned CDN loads with no SRI), then flip `csp_report_only` default to enforced. Add `frame-ancestors 'none'; base-uri 'self'; object-src 'none'`; add `Referrer-Policy` and `Permissions-Policy` headers. (`app/templates/base.html:20,27`; `app/middleware.py:106-112`)
- Escape the three operator/admin-controlled strings interpolated into HTML responses (`settings.py:172,471`; `routes/webhooks.py:381-383`) — self-XSS today, but trivially fixed by rendering a `partials/inline_message.html`.

### 1.4 Container & deployment
- `Dockerfile`: multi-stage; pin `python:3.11-slim@sha256:…`; `useradd -r app` + `USER app`; `HEALTHCHECK`; add `.dockerignore`. Split `requirements.txt` so pytest/httpx/pytest-cov are dev-only (they ship in the prod image today).
- `entrypoint.sh`: auto-generating `ENCRYPTION_KEY` when unset silently makes stored SMTP/OIDC secrets unreadable after every restart. Fail hard when `DEBUG` is false and no key is set; keep auto-gen for dev only.
- `docker-compose.prod.yml`: remove `POSTGRES_PASSWORD=postgres` and the dev API-key fallback (fail if unset); bind `127.0.0.1:8000` when behind a proxy.
- Info exposure: honor `metrics_enabled` (never checked), label `api_requests_total` by route template instead of raw path (currently leaks sync UUIDs and source names), drop `hostname` from unauthenticated `/version` or gate it. (`main.py:306,348-360`; `metrics.py:152-157`; `config.py:24`)

### 1.5 Ingest latency (perf + reliability)
- `create_sync_log` awaits `dispatch_webhooks` inline; the dispatcher sleeps `RETRY_DELAYS=[30,60,120]` between attempts, so one unreachable webhook holds the ingest HTTP request for minutes. Move dispatch to `BackgroundTasks` (or the existing background-task pattern) and return 201 immediately. (`app/api/endpoints/sync_logs.py:147`; `app/services/webhook_dispatcher.py:17,194-195`)

### 1.6 Minor
- `ApiKey.source_names` is defined but never enforced — enforce it in `create_sync_log` or drop the column (false sense of scoping). (`app/models/sync_log.py:47`)
- OIDC-created usernames skip `UserCreate` validation (length 50 column → possible 500; confusable names). Sanitize/truncate or use email. (`oidc.py:261,309-312`)
- First-admin race (`registration.py:61-62`): partial unique index or `SELECT … FOR UPDATE`.

---

## Phase 2 — Standards and quality-gate enforcement (~1 week, mostly config)

Goal: make the GA gates in `.claude/rules/quality-gates.md` real. **Order matters** — auto-fixable rules first, blocking structural rules only after Phase 3.

### 2.1 Ruff (staged rollout)
Current `ruff.toml` selects defaults (E/F) only. Proposed target:

```toml
target-version = "py311"
line-length = 88

[lint]
select = ["E","F","W","I","B","UP","S","N","C90","SIM","RUF","ASYNC","C4","T20","PT","ERA","D"]
ignore = [
  "E711","E712",              # SQLAlchemy == None / == True
  "B008",                     # FastAPI Depends()/Query() defaults (idiomatic)
  "S105","S106",              # token_type="bearer" false positives
  "D100","D104","D105","D107","D203","D212",
]

[lint.mccabe]
max-complexity = 10

[lint.pydocstyle]
convention = "google"

[lint.per-file-ignores]
"tests/**" = ["S101","S105","S106","D"]
"alembic/**" = ["D","E501"]
```

Staging (each its own `style:`/`refactor:` PR):
1. `I`, `UP` — 227 findings, all auto-fixable (`Optional[X]` → `X | None`).
2. `B`, `S`, `SIM`, `RUF`, `ERA`, `C4`, `ASYNC` — ~50 findings; `B904` (raise-from) ×9 and `S` ×6 need hand fixes. `S105` on `config.py:11` (`secret_key="change-me"`) is a real hit — keep the fail-fast, add a `# noqa` with reason.
3. `C90` (5 violations) — **after** Phase 3.2.
4. `D` (128 findings; 20 truly missing docstrings on models/config/lifespan) — last.

### 2.2 Mypy
`mypy.ini` disables `attr-defined`/`arg-type` for all of `app.api.endpoints.*` and four codes for `app.main` (stale — `main.py` has one `type: ignore` left). This hides exactly 6 real diagnostics (`users.py:65`, `sync_logs.py:215,275,280`, `analytics.py:234`), all SQLAlchemy column-expression false positives. Fix those with `sqlmodel.col()` (as `analytics.py` already does elsewhere), delete the blanket disables, then stage toward strict:

```ini
[mypy]
python_version = 3.11
disallow_untyped_defs = true     # step 1
warn_unreachable = true
plugins = pydantic.mypy
# strict = true                  # step 2 — currently 173 errors / 30 files

[mypy-slowapi.*,authlib.*,prometheus_client.*]
ignore_missing_imports = true
```

### 2.3 Dependencies
- Add a lockfile (`pip-compile`/`uv pip compile` → `requirements.lock` with hashes). Today `>=`-only pins mean the audited set ≠ the installed set (local venv shows 20 known CVE rows across starlette, python-multipart, pyjwt, urllib3; `pip-audit -r requirements.txt` is clean only because it resolves to latest).
- `.github/dependabot.yml` for pip, github-actions, docker (weekly).
- Note: the project venv is Python 3.13 while config/CI/Dockerfile say 3.11; pick one (3.11 per PRD) and pin the venv.

### 2.4 Pre-commit and CI
- `.pre-commit-config.yaml`: ruff check --fix, ruff format, mypy, gitleaks (or detect-secrets), check-added-large-files, end-of-file-fixer, conventional-pre-commit. Gate 1 currently depends on humans remembering to run ruff.
- `ci.yml`: GitHub auto-disabled this workflow for 60-day inactivity (found 2026-08-27; re-enabled with `gh workflow enable CI`). Either accept that a `gh workflow enable` may be needed after quiet periods, or add a `workflow_dispatch` trigger so runs can be started manually without close/reopen tricks. Add gitleaks step; add `alembic check` (from 0.4); add an E2E job using `tests/e2e/docker-compose.e2e.yml` on PRs to `main` (77 Playwright tests never run in CI); scope `permissions: contents: write, packages: write` to the `build-push` job only; pin actions to SHAs; add a Trivy/Grype scan after build.

### 2.5 Tests
- `.add/config.json` says `unit: pytest tests/unit/` and `integration: pytest tests/integration/`, but `tests/integration/` is empty and ~45 test files sit flat in `tests/`. Either move files into `unit/`/`integration/` or fix the config so the gate command runs the whole suite.
- Promote duplicated helpers to `conftest.py` factories: `_create_user`/`_make_client` (copied in 9 files), `create_webhook` (5×), `create_failure_event` (4×), `sqlite_engine` (4×).
- Five files spin up SQLite and mutate `SQLModel.metadata` globally (JSONB → JSON), which persists for the process and is order-dependent (`tests/test_sync_filters.py:27-33` and siblings). Use Postgres everywhere or copy the metadata.
- 329 client-fixture tests each run `bcrypt.hashpw` at cost 12 (`conftest.py:131-135`); hash once at module scope or set rounds to 4 under test.
- ~29% of tests don't follow `test_acNNN_` naming; enforce for new tests only.

### 2.6 API contract consistency
- Two `ErrorResponse` models exist (`app/errors.py:20` vs `app/schemas/sync_log.py:152`); endpoints advertise the second in OpenAPI but the app returns the first. Delete the schema copy.
- Pagination: `sync-logs` returns `PaginatedResponse{items,total,cursor}`, `analytics/export` uses `limit/offset` with default 10,000, and monitors/webhooks/failures/users/api-keys return bare arrays. Adopt the envelope everywhere or document unbounded lists as intentional.

### 2.7 Repo hygiene
- Delete duplicate `.github/pull_request_template.md` (identical to `PULL_REQUEST_TEMPLATE.md`).
- `CHANGELOG.md` top release is 2.3.1; tags reach v2.6.0 — auto-tagging outpaces the changelog. Add a release step that promotes `[Unreleased]`.
- README says Python 3.13 on line 229 and 3.11+ on line 39.
- Two unmerged branches are >5 months old vs the GA 14-day rule: merge/close `feature/oidc-signature-verification` (PR #35) and finish `feature/performance-optimization` (this branch — blocked on 0.4).
- Add `SECURITY.md`, `CODEOWNERS`.

---

## Phase 3 — Maintainability refactors (2–3 cycles; ADD `refactor:` PRs, behaviour-preserving)

Spec: `specs/service-layer-refactor.md` with ACs of the form "REST and HTMX paths produce identical persisted state for input X" so the refactor is test-driven.

### 3.1 Service layer (removes REST/HTMX drift)
Every feature is implemented twice with logic in handlers. `registration.py`, `sync_filters.py`, and `webhook_test.py` show the intended pattern — apply it consistently:

| Service to create | Replaces duplicated logic in |
|---|---|
| `services/webhooks.py` (create/update/delete/toggle on a validated dataclass) | `routes/webhooks.py:95-174,199-305` and `api/endpoints/webhooks.py:86-178` (the two HTMX handlers are also near-copies of each other) |
| `services/api_keys.py` (`create_api_key(session, user, name, role_override) -> (ApiKey, raw_key)`) | `routes/api_keys.py:64-127`, `api/endpoints/api_keys.py:35-76`, `routes/settings.py:639-654` (three copies of `"rsv_" + token_urlsafe(32)`) |
| `services/users.py` (role change / toggle / delete with last-admin guard, raising a domain error) | `routes/admin.py:58-140`, `api/endpoints/users.py:69-177` |
| `services/sync_ingest.py` (parse → persist → metrics → failure event → monitor → schedule webhooks) | `api/endpoints/sync_logs.py:67-158` |
| extend `services/sync_filters.py` to accept `date` objects | filter block copy-pasted at `sync_logs.py:219-229`, `analytics.py:94-100,158-168,237-249` |
| `deps.py`: `_extract_token(request)` + `_resolve_user(session, token, raise_errors)` | JWT extraction written 3× (`deps.py:124-180,194-220,300-340`); `verify_api_key` ≈ `_try_verify_api_key` |

### 3.2 God functions / god files (unblocks Phase 2.1 step 3)
- `list_sync_logs` (181 lines, complexity 15): split offset and cursor pagination into helpers; fixes 0.10 naturally.
- `run_synthetic_check` (129 lines): the failure-event + webhook block is duplicated at `synthetic_check.py:325-342` and `388-405`.
- `htmx_notifications` (114), `htmx_webhook_update` (107), `htmx_monitoring_generate` (98), `dispatch_webhooks` (95).
- Split `routes/settings.py` (681 lines) into `settings_smtp.py`, `settings_oidc.py`, `settings_synthetic.py`, `monitoring_wizard.py`; the SMTP and OIDC save handlers share an identical shape (encryption-key guard → form → validate → get-or-create singleton → re-encrypt → render) worth one helper. Move the compose-YAML generator (`settings.py:520-561`) into a Jinja template.
- Consider raising `maxFileLength` to 500 in `.add/config.json qualityChecks` rather than splitting `deps.py`/`main.py`/`oidc.py` purely for the number.

### 3.3 Error handling
- `http_exception_handler` derives `error_code` by substring-matching `exc.detail` ("not found" → `RESOURCE_NOT_FOUND`, everything else → `BAD_REQUEST`, including 403s). Introduce `AppError(HTTPException)` carrying `error_code`, or map from status code. (`app/main.py:183-204`)
- HTMX success/error markup is hand-built as raw strings 24× (`settings.py` 16, `webhooks.py` 8) with hard-coded classes; `settings.py:470-472` returns 200 on discovery failure. Render `partials/inline_message.html` with proper status codes.
- Handlers call other handlers to build responses (`routes/webhooks.py:172,303,327,349`; `admin.py:89,113,140`; `api_keys.py:150`). Extract `_render_webhook_list(request, session)`.

### 3.4 Auth pattern unification
- Three REST auth styles today (`require_role_or_api_key` / `ApiKeyDep` / none). After 0.1 and 0.8, add router-level `dependencies=[...]` so a new endpoint cannot be added unauthenticated by omission.
- HTMX routes repeat `if not user or not role_at_least(...)` 21× because `AdminDep` returns JSON 403 (`routes/admin.py:17-19`). Add `require_role_html(min_role)` that raises an HTML 403.

### 3.5 Global state and worker-safety
- `synthetic_check.py:78-82` module globals (`_state`, `_background_task`) are per-process: with multiple uvicorn workers, toggling in the UI affects one worker and `/health` reports a per-worker status. Wrap in a `SyntheticMonitor` on `app.state` (single worker) or persist `last_status` to the existing `synthetic_check_results` table.
- `oidc.py:59,94` in-process `_discovery_cache` / `_pending_states` — OIDC login breaks when the callback lands on a different worker. Store pending state in a signed cookie or DB row.
- `deps.py:100-102,253-255` run `_lookup_and_verify_api_key` (which calls `session.commit()`) on a thread-pool thread with the request-scoped Session. Works only by accident; offload only `bcrypt.checkpw` (as `routes/auth.py:57-60` does) and keep DB access on the request thread. (Becomes simpler after 0.3 removes the scan.)
- `routes/settings.py:346-371` imports `engine` directly and starts/stops the background task from a request handler.

### 3.6 Small cleanups
- `asyncio.get_event_loop()` inside coroutines (`routes/auth.py`, `api/endpoints/auth.py`, `api/deps.py`) → `asyncio.get_running_loop()`.
- 32 imports inside function bodies (`synthetic_check.py`, `settings.py`, `oidc.py`, `users.py`, `main.py:322`) — none are real cycles; hoist them.
- Delete the `main.py:73-81` re-export shim and update tests to import from `app.templating`; drop the module-level `_start_time`/`_hostname` fallbacks duplicating `app.state`.
- Naming: `*Read` vs `*Response` schemas; `settings_cfg`/`settings`/`current_settings`; `_form_str()` vs `str(form.get())`.
- Name the magic numbers (`dashboard.py:63,145`; `settings.py:361-364,407-409`; `pages.py:161-162`; `deps.py:73`; `stale_checker.py:35`; `email.py:147`; `oidc.py:76,178`; `webhook_dispatcher.py:107`).
- Docstrings on the 20 public exports that lack them (models, `Settings`, `get_settings`, `get_session`, `lifespan`).

---

## Dependency graph

```
Phase 0 (hotfixes, independent, parallelisable)
  0.4 alembic migration ──► unblocks merging feature/performance-optimization
  0.3 rate-limit/scan ───► simplifies 3.5 session-thread fix
Phase 1 (security depth) ── independent of Phase 3, can interleave
Phase 3.1 + 3.2 (service layer, god functions) ──► Phase 2.1 step 3 (C90 blocking)
                                                 ──► Phase 2.1 step 4 (D blocking)
Phase 2.2–2.7 (mypy, lockfile, pre-commit, CI, tests, hygiene) ── start any time
```

## Effort estimate

| Phase | Size | Notes |
|---|---|---|
| 0 | 1–2 days | ten small PRs; write the spec first (~1 h) |
| 1 | ~1 week | SSRF guard and CSRF rewrite are the two non-trivial pieces |
| 2 | ~1 week | mostly config; test reorg is the slow part |
| 3 | 2–3 cycles | service extraction is mechanical but wide; do webhooks first (largest drift) |

## What NOT to change
bcrypt/token hashing scheme, cookie flags, refresh-token rotation, `_safe_return_url`, OIDC state/nonce handling, Fernet secret storage, the N+1 batching patterns, keyset pagination design, structured logging — all reviewed and sound.
