# Implementation Plan: Insight UI (M16)

**Spec:** specs/insight-ui.md · **UX:** specs/ux/insight-ui-ux.md (DRAFT)
**Date:** 2026-08-29
**Maturity:** GA — TDD per task, one PR per cycle, PR review before merge, production deploy on merge (auto-tag).

## Status (2026-08-29)

| Cycle | Status |
|-------|--------|
| C1 | **DONE** — PR #42 → v2.7.0 |
| C2 | **DONE** — PR #43 → v2.8.0 |
| C3 | **DONE** — `feature/spa-scaffold` → v2.9.0. Notes: Vite 8 template ships oxlint (not ESLint) and TypeScript 6; `npm ci --ignore-scripts` is required because `fsevents` has no prebuilt binary for Node 26 and its node-gyp build hangs, while rolldown/oxlint platform binaries are *optional* deps that must stay installed (do not use `--omit=optional`). Recharts resolved to 3.x. |
| C4 | **code complete** — `feature/spa-transfers-trends` (branched after C3 merge). Recharts 3 chart `onClick` receives `activeIndex` (no `activePayload`); status=failed is a client-side filter because the list API has no exit-code filter. |
| C5 | **code complete** — Media + Uptime pages; "originating transfer" links open Transfers filtered to the item's day + source (the list API has no per-sync deep link yet). |
| C6 | **DONE** — PR #48 → v2.12.0. `/` served by `app/routes/spa.py` with `window.__USER__`/`__USER_THEME__` injected at the top of `<head>` (keeps the FOUC-prevention and role-aware menu without a round trip); legacy dashboard routes/templates/tests removed; `/notifications` server-rendered page keeps the HTMX history partial; E2E dashboard/analytics/login rewritten. Lesson: GitHub closes a stacked PR when its base branch is deleted — merge stacked PRs bottom-up or retarget before deleting. |

## Cycles (each one PR, independently shippable)

| Cycle | Branch | Scope | ACs | Size |
|-------|--------|-------|-----|------|
| **C1** | `feature/insight-api` | Backend: synthetic status/history API, sources health API, SPA serving route | AC-002, AC-003, AC-005, AC-022 | M |
| **C2** | `feature/media-catalog` | Backend: media classifier, `media_items` table + migration, ingest hook, `/media/*` API, backfill script | AC-016–AC-021 | M |
| **C3** | `feature/spa-scaffold` | `frontend/` scaffold, shell + liveness pill + nav, Overview page, CI job, Docker Node stage | AC-001, AC-006, AC-007, AC-008, AC-023, AC-025, AC-026 | L |
| **C4** | `feature/spa-transfers-trends` | Transfers page (grouping, inline detail, URL filters), Trends page (linked charts, source table) | AC-009–AC-015 | L |
| **C5** | `feature/spa-media-uptime` | Media page, Uptime page | AC-004, AC-019 | M |
| **C6** | `feature/spa-cutover` | `/` serves SPA, legacy dashboard removed, E2E rewritten, screenshots, responsive pass | AC-024, AC-027 | M |

C1 and C2 are backend-only and can ship before any frontend exists (C2 is independent of C1). C3 depends on C1 (pill + health cards). C4 needs nothing new from the backend. C5 depends on C1 + C2. C6 last.

Frontend versions are `feat:` commits → each SPA cycle bumps the minor version on merge; C3 will ship as v2.7.0 with the SPA reachable at `/app` while `/` still serves the legacy dashboard (safe, opt-in preview until C6).

---

## C1 — Insight API

### T1. Synthetic status + history endpoints (AC-002, AC-003)
RED — `tests/test_insight_api.py`:
- `test_ac002_status_disabled_when_no_config` → `{enabled: false, status: "disabled", uptime_24h_pct: null}`
- `test_ac002_status_uptime_from_results` — seed 10 results (9 passing) in last 24 h → `uptime_24h_pct == 90.0`, `checks_24h == 10`, `status` = latest result
- `test_ac002_requires_auth` → 401 unauth; viewer JWT 200
- `test_ac003_history_newest_first_and_limit` — seed 5, `limit=3` → 3 rows, descending `checked_at`; `limit=0`/`501` → 422
GREEN — `app/api/endpoints/synthetic.py` (router `/synthetic`, router-level viewer guard), `app/schemas/synthetic.py`; uptime = passing/total over window from `SyntheticCheckResultRecord`; `status` from latest record, `enabled` + `interval_seconds` from `SyntheticCheckConfig` (fallback to in-process `get_state()` if no rows yet). Register in `main.py`.

### T2. Sources health endpoint (AC-005)
RED:
- `test_ac005_health_per_source_with_daily_series` — seed 3 sources, mixed statuses across 3 days → per-source `last_status`, `consecutive_failures`, 14-entry `daily` (zero-filled)
- `test_ac005_stale_from_monitor` — monitor `expected_interval_hours=1`, last sync 3 h ago → `is_stale: true`
- `test_ac005_excludes_synthetic_and_dry_runs`
GREEN — `app/api/endpoints/sources.py` + `app/services/source_health.py`: one grouped query for daily aggregates (`date_trunc('day', start_time)`), one window query for last sync per source (`DISTINCT ON (source_name) … ORDER BY source_name, start_time DESC`), monitors joined in Python. Reuse `stale_checker` logic for `is_stale`.

### T3. SPA serving route (AC-022)
RED — `tests/test_spa_serving.py`: `GET /app` and `/app/media` return 200 HTML containing `id="root"` when `app/static/app/index.html` exists (fixture writes a stub file into a tmp dir and monkeypatches the path); 404 JSON with a helpful message when the build is missing; unauth `/app` → 302 `/login?return_url=/app`.
GREEN — `app/routes/spa.py`: `@router.get("/app")`, `@router.get("/app/{path:path}")` → `FileResponse(index, headers={"Cache-Control": "no-store"})`; path resolved from `settings.spa_dist_dir` (default `app/static/app`). Add `app/static/app/` to `.gitignore`.

VERIFY C1: ruff, mypy, full suite, CHANGELOG `[Unreleased] → Added`.

---

## C2 — Media catalogue

### T4. Classifier (AC-016, AC-021)
RED — `tests/test_media_classifier.py` (pure functions, table-driven, ~25 cases): Plex movie dir + file, dotted release names, `SxxEyy`, `1x05`, `Season 02/… E03`, sidecar `.srt` ignored, photos ignored, `Movies/movie_112.mkv` → movie no year, trailing slash dir ignored, tag stripping (`WEBDL-1080p.EAC3 Atmos.x264` → title clean), unicode titles, Windows-style backslashes.
GREEN — `app/services/media_classifier.py`: `classify_path(path) -> MediaMatch | None`, `classify_file_list(paths) -> list[MediaMatch]` (dedupe within a log).

### T5. Model, migration, ingest hook, backfill (AC-017, AC-020)
RED — `tests/test_media_items.py`: ingest a log via `POST /sync-logs` with mixed paths → rows created; ingest again → same count; dry run → none; synthetic source → none; `scripts/backfill_media.py` over existing logs is idempotent; `alembic check` clean (existing drift test covers it).
GREEN — `app/models/media_item.py`; Alembic revision (table + unique expression index); `app/services/media_catalog.py: record_media(session, sync_log)` using `INSERT … ON CONFLICT DO NOTHING`; call from `create_sync_log` after commit (wrapped in try/except + log — never fails ingestion); `scripts/backfill_media.py` (batched by `created_at`).

### T6. Media API (AC-018)
RED — `tests/test_media_api.py`: `new?days=7` groups episodes by show and lists movies, ordered by `first_seen_at desc`; `kind=movie` filters; `summary` counts; older items excluded; auth 401/200.
GREEN — `app/api/endpoints/media.py`, `app/schemas/media.py`.

VERIFY C2 as C1.

---

## C3 — SPA scaffold + Overview

### T7. Scaffold and toolchain (AC-025)
- `npm create vite@latest frontend -- --template react-ts`; add React Router, TanStack Query, Recharts, Tailwind 4, date-fns, Vitest, Testing Library, MSW, ESLint (typescript-eslint + react-hooks), Prettier.
- `vite.config.ts`: `base: '/static/app/'`, `build.outDir: '../app/static/app'`, dev proxy `/api`, `/login`, `/health` → `http://localhost:8000`.
- `frontend/src/api/` typed client (`fetchJson`, 401 redirect), `frontend/src/api/types.ts` hand-written from the Pydantic schemas (keep in sync; optional later: generate from OpenAPI).
- CI: new `frontend` job (`npm ci`, `npm run lint`, `npm run typecheck`, `npm run test -- --coverage`, `npm run build`); coverage threshold 80 % in `vitest.config.ts`.
- Dockerfile: `FROM node:22-alpine AS frontend` → `COPY --from=frontend /frontend/dist /app/app/static/app`; `Dockerfile.test` unchanged (backend tests don't need the build); `.dockerignore` for `node_modules`.
- README "Frontend development" section (`cd frontend && npm run dev` with proxy).

### T8. Shell, liveness pill, nav, theme (AC-001, AC-007, AC-023)
RED (vitest + MSW): pill renders UP/DOWN/off from `/synthetic/status`; refetch interval equals `interval_seconds`; nav shows five items and the settings menu respects role from `/users/me` (add `GET /api/v1/users/me` if missing — check `users.py`; else derive from `/users/me/preferences` + a new lightweight `me` endpoint in C1 if needed); theme bootstrap sets `data-theme`.
GREEN — `src/app/Shell.tsx`, `src/features/liveness/LivenessPill.tsx`, `src/app/router.tsx`.

### T9. Overview page (AC-006, AC-008, AC-026)
RED: health cards render one per source with status class and sparkline; click navigates to `/app/transfers?source=`; activity strip groups last 7 days from `/sync-logs` (local-date grouping) and expands inline; empty state shows the CTA; error state shows retry.
GREEN — `src/features/overview/*`, shared `src/features/transfers/SyncRow.tsx` + `SyncDetail.tsx` (reused in C4).

E2E (Playwright, python): `tests/e2e/test_insight_ui.py::test_tc001_overview_glance` with screenshot step-01.

---

## C4 — Transfers + Trends

### T10. Transfers page (AC-009–AC-012)
RED: grouping day→source→sync; filters ⇄ URL; infinite scroll requests next cursor; expanding a row fetches `/sync-logs/{id}` once and shows raw tail for failures; virtualised file list for >200 files.
GREEN — `src/features/transfers/*`; `react-virtual` for the file list.

### T11. Trends page (AC-013–AC-015)
RED: four charts share a hovered date (synchronised tooltip state); source row click sets `source` param and re-queries; bar click navigates to Transfers with `from`/`to`.
GREEN — `src/features/trends/*`.

E2E: TC-003, TC-004 (screenshot step-03).

---

## C5 — Media + Uptime

### T12. Media page (AC-019) — RED: counts, show groups with episode labels, movies list, link to transfer. GREEN — `src/features/media/*`. E2E TC-005 (step-04).
### T13. Uptime page (AC-004) — RED: 100-cell timeline, failing cell tooltip shows error, latency chart, disabled state. GREEN — `src/features/uptime/*`. E2E TC-006 (step-05).

---

## C6 — Cut-over

### T14. `/` serves SPA; legacy removal (AC-024)
- `pages.py`: `/` → SPA index; `/analytics` and `?tab=` → `/app/trends`; delete `index.html`, `analytics.html`, `partials/sync_table|sync_detail|charts|analytics|notifications_list.html`, `routes/dashboard.py`, and their unit tests (`test_htmx.py`, `test_date_range_*`, `test_analytics` UI parts, `test_notification_history` UI parts — keep API tests).
- Notifications history: not in the SPA nav this milestone → move to the ⚙ menu as a server-rendered page? **Decision:** keep `/htmx/notifications` reachable from a small `/notifications` server-rendered page (low-frequency screen, same treatment as settings) — do not delete.
- Rewrite `tests/e2e/test_dashboard.py`, `test_analytics.py` against SPA selectors (`data-testid`); capture all six screenshots.
### T15. Responsive pass (AC-027) — vitest snapshot at 375 px is weak; rely on Playwright mobile viewport test (TC-009, step-06).

---

## File changes (summary)

| Area | Create | Modify |
|------|--------|--------|
| Backend API | `app/api/endpoints/{synthetic,sources,media}.py`, `app/schemas/{synthetic,source_health,media}.py`, `app/services/{source_health,media_classifier,media_catalog}.py`, `app/models/media_item.py`, `app/routes/spa.py`, `alembic/versions/<media_items>.py`, `scripts/backfill_media.py` | `app/main.py` (routers, model import), `app/api/endpoints/sync_logs.py` (ingest hook), `app/config.py` (`spa_dist_dir`), `alembic/env.py` (model import), `.gitignore` |
| Frontend | `frontend/**` | `Dockerfile`, `.dockerignore`, `.github/workflows/ci.yml`, `README.md` |
| Cut-over | `tests/e2e/test_insight_ui.py` | `app/routes/pages.py`, template/route deletions, E2E rewrites |

## Test strategy
- Backend: pytest against Postgres (existing fixtures); classifier tests are pure-function table tests.
- Frontend: Vitest + Testing Library + MSW handlers mirroring the API contract in `frontend/src/test/handlers.ts`; coverage ≥ 80 %.
- E2E: existing Python Playwright harness (`tests/e2e/docker-compose.e2e.yml`) — the image now contains the built SPA.
- Contract drift guard: a backend test asserts the OpenAPI schema contains the new endpoints; frontend types are reviewed against it at each cycle (generation deferred).

## Risks
| Risk | Mitigation |
|------|------------|
| Media heuristics misclassify unusual layouts | Table-driven tests; unknown → ignored, never wrong-kind; rules documented in spec §4 |
| Node stage slows CI/Docker | Cache `node_modules` (`cache-from: gha`), `npm ci` |
| E2E churn at cut-over | SPA uses stable `data-testid`s from C3 onward |
| UX not yet signed off | C1/C2 are UI-agnostic; C3 starts with the shell — cheap to adjust after review |

## Spec traceability
See per-task AC lists above; every AC-001…AC-027 is assigned to exactly one task.
