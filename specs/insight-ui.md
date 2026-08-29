# Spec: Insight UI — Interactive Dashboard Rebuild

**Version:** 0.1.0
**Created:** 2026-08-29
**PRD Reference:** docs/prd.md §5 (frontend architecture decision), §6 M16
**Status:** IMPLEMENTED — C1–C6 (2026-08-29); UX artifact still awaiting human sign-off
**Milestone:** M16 — Insight UI
**UX artifact:** specs/ux/insight-ui-ux.md
**Plan:** docs/plans/insight-ui-plan.md

## 1. Overview

The current dashboard is a tab bar, a filter form, and a table: every piece of information costs a click and nothing is learned by looking. This feature replaces it with an insight-first single-page application that answers, in order of importance:

1. **Is the system alive and syncing?** — synthetic-monitoring uptime and source liveness, always visible.
2. **What was sent?** — a condensed activity feed per day/source, expandable to files and failure details.
3. **How are transfers trending?** — bytes, files, duration, and success over time, with source comparison and cross-filtering.
4. **What new shows and movies arrived?** — media titles derived from rsync file lists, not raw paths.
5. **Settings** — reachable, but demoted to a secondary destination.

The SPA (React + TypeScript + Vite) is served by the existing FastAPI app from the same container and talks to `/api/v1` with the existing `access_token` cookie. Login, settings, and admin screens stay server-rendered in this milestone.

### User Story

As a **homelab operator who runs scheduled rsync jobs for media and backups**, I want the dashboard to show me at a glance whether everything is up, what arrived recently (including which shows and movies), and how transfer volume is trending — with the ability to drill into any day, source, or transfer — so that I understand my sync activity without clicking through tables.

## 2. Acceptance Criteria

### Liveness (synthetic monitoring + sources)

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Every SPA page header shows a liveness pill: synthetic status (`passing`/`failing`/`disabled`), uptime % over the last 24 h, and age of the last check ("checked 2m ago"). It refreshes automatically at the configured check interval without a page reload. | Must |
| AC-002 | `GET /api/v1/synthetic/status` returns `{enabled, status, last_check_at, last_latency_ms, interval_seconds, uptime_24h_pct, uptime_7d_pct, checks_24h}`; requires viewer. | Must |
| AC-003 | `GET /api/v1/synthetic/history?limit=N` (default 100, max 500) returns the most recent check results `[{checked_at, status, latency_ms, error}]`, newest first; requires viewer. | Must |
| AC-004 | The Uptime page renders the history as a status timeline (one cell per check, colour by status) plus a latency chart; a failing check exposes its `error` on hover/tap. | Must |
| AC-005 | `GET /api/v1/sources/health` returns, per non-synthetic source: `{source_name, last_sync_at, last_status, last_exit_code, consecutive_failures, expected_interval_hours (nullable), is_stale, daily: [{date, syncs, failures, bytes}] (14 days)}`; requires viewer. | Must |
| AC-006 | The Overview shows one health card per source with a status colour (ok / failing / stale / never), last-sync relative time, and a 14-day sparkline; clicking a card opens the Transfers page filtered to that source. | Must |
| AC-007 | When synthetic monitoring is disabled, the pill reads "Synthetic check off" with a link to `/settings` (operator+) and nothing else on the page is blocked. | Must |

### Transfers (what was sent)

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-008 | The Overview activity strip lists the last 7 days as rows of `date · N syncs · M failed · total bytes · top sources`; each row expands inline to the day's transfers without navigation. | Must |
| AC-009 | The Transfers page groups syncs by day, then source; each group header shows count, bytes, files, and failures; each sync row shows source, start time (relative within 24 h), duration, bytes, files, status. | Must |
| AC-010 | Expanding a sync row shows its file list (virtualised for >200 entries), speedup ratio, and — on failure — exit code and the raw rsync output tail; no second navigation needed. | Must |
| AC-011 | Transfers supports filters for source, date range (7d / 30d / 90d / custom), status (all / failed), and hides dry runs and synthetic syncs by default, using the existing `GET /api/v1/sync-logs` cursor API with infinite scroll. | Must |
| AC-012 | Filters are reflected in the URL query string so a filtered view can be linked and restored on reload. | Should |

### Trends (transfers over time)

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-013 | The Trends page shows four linked charts (bytes, files, duration, success/failure) from `GET /api/v1/analytics/summary` for the selected period and range; hovering a date highlights it across all four. | Must |
| AC-014 | A per-source comparison table (from `GET /api/v1/analytics/sources`) lists total syncs, success rate, avg duration, avg bytes; clicking a source filters the charts to it. | Must |
| AC-015 | Clicking a point on any chart opens the Transfers page filtered to that date (and source, if selected). | Should |

### Media (new shows and movies)

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-016 | On sync-log ingestion, file paths are classified into media items: **episode** (path contains `SxxEyy`, `NxNN`, or `Season N/…`) or **movie** (`Title (YYYY)` directory or file, no episode marker); only video extensions (`mkv mp4 m4v avi mov ts wmv webm`) create items; dry runs and the synthetic source are skipped. | Must |
| AC-017 | Items are stored in `media_items` with `(kind, title, year, season, episode)` unique; the first sighting sets `first_seen_at`, `source_name`, `sync_log_id`, `path`. Re-syncing the same file never creates a duplicate. | Must |
| AC-018 | `GET /api/v1/media/new?days=7&kind=show\|movie` returns items first seen in the window, grouped for shows by title with their new episodes, and `GET /api/v1/media/summary?days=7` returns `{new_movies, new_shows, new_episodes}`; both require viewer. | Must |
| AC-019 | The Media page shows "New this week" counts and two lists — Shows (title, new-episode count, latest `S01E05` label) and Movies (title, year) — each linking to the originating transfer. | Must |
| AC-020 | Existing sync logs can be back-filled with `python -m scripts.backfill_media` (idempotent). | Must |
| AC-021 | Unclassifiable paths are ignored silently; a sync log with no media never errors ingestion. | Must |
| AC-028 | rsync control lines that end up in `file_list` are never classified as media: `deleting …` and itemized `*deleting …`, `created directory …`, `sending/receiving incremental file list`, `--stats` summary lines (`Number of …`, `Total …`, `Literal/Matched data`, `File list …`), and attribute-only/hard-link itemize lines. Itemized transfer lines (`>f…`, `<f…`, `cf…` + path) are classified by their path. | Must |
| AC-029 | A deletion line for a known item sets `media_items.removed_at` (to the sync's `start_time`); a directory deletion (`deleting dir/`) retires every item of that source whose path is under the directory; a later transfer of the same item clears `removed_at` without changing `first_seen_at`. Retired items are excluded from `/media/new` and `/media/summary`. Deletions are applied before transfers within one log. | Must |
| AC-030 | A migration adds `removed_at` and repairs phantom rows created from deletion lines: when the real item exists it is retired at the phantom's `first_seen_at` and the phantom deleted; otherwise the phantom becomes the real item (path, title and dedupe key corrected) marked removed. Re-running `scripts.backfill_media` applies historical deletions. | Must |

### Navigation, serving, and quality

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-022 | The SPA is served at `/app` (assets under `/static/app/`) with a catch-all so deep links (`/app/media`) load; unauthenticated requests redirect to `/login?return_url=…` via the existing middleware. | Must |
| AC-023 | Navigation order is Overview · Transfers · Trends · Media · Uptime; Settings and Admin are a secondary menu (icon/avatar) linking to the existing server-rendered pages; the theme follows the stored user preference. | Must |
| AC-024 | After cut-over, `GET /` serves the SPA; the legacy Jinja dashboard routes (`index.html`, `/htmx/sync-table`, `/htmx/analytics`, `/htmx/charts`, `/htmx/notifications`) are removed along with their tests, and Playwright E2E tests for dashboard/analytics are rewritten against the SPA. | Must |
| AC-025 | Frontend quality gates run in CI: `eslint`, `tsc --noEmit`, `vitest --coverage` (≥ 80 % lines), and the SPA build; the production image builds the SPA in a Node stage (no CDN scripts; CSP-compatible). | Must |
| AC-026 | Every page has loading, empty, and error states; the empty Overview (no syncs yet) shows the monitoring-setup call to action. | Must |
| AC-027 | Layout is responsive: no horizontal scroll at 375 px; health cards stack; charts remain readable. | Should |

## 3. User Test Cases

### TC-001: Glance check
**Precondition:** Synthetic monitoring enabled, 3 sources syncing, one failing.
**Steps:** Open `/app`.
**Expected:** Within one screen: liveness pill green with uptime %, three health cards (one red), activity strip for 7 days. No clicks.
**Screenshot Checkpoint:** `tests/screenshots/insight-ui/step-01-overview.png`
**Maps to:** AC-001, AC-006, AC-008

### TC-002: Drill into a failure
**Precondition:** A failed sync yesterday.
**Steps:** On Overview, expand yesterday's activity row; click the failed sync.
**Expected:** Row expands inline with exit code, raw output tail, and file list. Two clicks total.
**Screenshot Checkpoint:** `step-02-failure-drilldown.png`
**Maps to:** AC-008, AC-010

### TC-003: Filtered transfers via URL
**Steps:** Open `/app/transfers?source=movies&range=30d&status=failed`; reload.
**Expected:** Grouped list shows only failed `movies` syncs in the last 30 days; filters persist after reload.
**Maps to:** AC-009, AC-011, AC-012

### TC-004: Linked trends
**Steps:** Open Trends, hover a date on the bytes chart; click a source in the comparison table.
**Expected:** All four charts highlight the same date; charts re-query for the selected source.
**Screenshot Checkpoint:** `step-03-trends.png`
**Maps to:** AC-013, AC-014

### TC-005: New media
**Precondition:** Ingest a log with `The Polar Express (2004)/….mkv` and `Severance (2022)/Season 02/Severance - S02E03 - ….mkv`.
**Steps:** Open Media.
**Expected:** Movies lists "The Polar Express (2004)"; Shows lists "Severance" with 1 new episode (S02E03). Ingesting the same log again changes nothing.
**Screenshot Checkpoint:** `step-04-media.png`
**Maps to:** AC-016–AC-019

### TC-008: Deleted media never shows as new
1. Ingest a log whose file list contains `deleting Movies/Old Film (2001)/Old Film.mkv` and a real transfer `Movies/New Film (2024)/New Film.mkv`.
2. Media page shows only *New Film*; the summary counts one movie.
3. Ingest a second log with `deleting Movies/New Film (2024)/` — *New Film* disappears from the page.
4. Ingest a third log transferring `Movies/New Film (2024)/New Film.mkv` again — it reappears but is not counted as new (original `first_seen_at` kept).
**Maps to:** AC-028–AC-030

### TC-006: Uptime history
**Precondition:** ≥ 50 synthetic checks with a failing streak.
**Steps:** Open Uptime; hover a red cell.
**Expected:** Timeline shows the streak; tooltip shows the error text; latency chart present.
**Screenshot Checkpoint:** `step-05-uptime.png`
**Maps to:** AC-003, AC-004

### TC-007: Synthetic disabled
**Steps:** Disable synthetic monitoring in settings; open `/app`.
**Expected:** Pill reads "Synthetic check off" with a settings link; everything else renders.
**Maps to:** AC-007

### TC-008: Deep link while logged out
**Steps:** Log out; open `/app/media`.
**Expected:** Redirect to `/login?return_url=/app/media`; after login, land on Media.
**Maps to:** AC-022

### TC-009: Mobile
**Steps:** Open `/app` at 375 px width.
**Expected:** No horizontal scroll; cards stacked; pill still visible.
**Screenshot Checkpoint:** `step-06-mobile.png`
**Maps to:** AC-027

## 4. Data Model

### New table: `media_items`

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| kind | str(10) | `movie` \| `episode` |
| title | str(200) idx | Show or movie title, cleaned (dots → spaces, release tags stripped) |
| year | int nullable | From `(YYYY)` |
| season | int nullable | episodes only |
| episode | int nullable | episodes only |
| path | str(1024) | first path that produced the item |
| source_name | str(100) idx | |
| sync_log_id | UUID FK sync_logs.id (ON DELETE SET NULL) | first sighting |
| first_seen_at | datetime idx | = sync log `start_time` of first sighting |
| created_at | datetime | |

Unique index on `(kind, title, year, season, episode)` (NULLs treated as distinct in PostgreSQL — use `COALESCE` expression index: `(kind, title, coalesce(year,0), coalesce(season,-1), coalesce(episode,-1))`).

Retention: when `sync_logs` rows are deleted by retention, `sync_log_id` becomes NULL; media items persist (they are the catalogue).

### Classification rules (`app/services/media_classifier.py`)

```
episode markers (case-insensitive): S(\d{1,2})E(\d{1,3})  |  (\d{1,2})x(\d{2,3})  |  /Season (\d{1,2})/ … E(\d{1,3})
movie: last dir or file stem matches ^(?P<title>.+?)[ .]\((?P<year>(19|20)\d{2})\)   and no episode marker
title source: for episodes, first path segment (strip trailing "(YYYY)"); for movies, the matched title
cleanup: replace '.' and '_' with ' ', collapse spaces, strip known tags (1080p, 2160p, WEBDL, WEB-DL, Bluray, x264, x265, HEVC, EAC3, Atmos, AAC, h264, DTS, REMUX, PROPER, REPACK)
only extensions: .mkv .mp4 .m4v .avi .mov .ts .wmv .webm
skip: dry runs, source == __synthetic_check, paths ending with '/', sidecar files (.srt .nfo .jpg …)
```

## 5. API Contract

All new endpoints require viewer via `require_role_or_api_key(ROLE_VIEWER)` and are router-level guarded.

| Method | Path | Query | Response |
|--------|------|-------|----------|
| GET | `/api/v1/synthetic/status` | — | `SyntheticStatus{enabled, status, last_check_at, last_latency_ms, interval_seconds, uptime_24h_pct, uptime_7d_pct, checks_24h}` |
| GET | `/api/v1/synthetic/history` | `limit` (1–500, default 100) | `list[SyntheticCheckRead{checked_at, status, latency_ms, error}]` |
| GET | `/api/v1/sources/health` | `days` (1–90, default 14) | `list[SourceHealth{source_name, last_sync_at, last_status, last_exit_code, consecutive_failures, expected_interval_hours, is_stale, daily: list[DailyPoint{date, syncs, failures, bytes}]}]` |
| GET | `/api/v1/media/new` | `days` (1–90, default 7), `kind` (`show`\|`movie`, optional) | `MediaNewResponse{days, shows: list[ShowGroup{title, year, new_episodes: list[EpisodeRead{season, episode, first_seen_at, sync_log_id, source_name}]}], movies: list[MovieRead{title, year, first_seen_at, sync_log_id, source_name}]}` |
| GET | `/api/v1/media/summary` | `days` | `{days, new_movies, new_shows, new_episodes}` |

Existing endpoints consumed unchanged: `/sync-logs` (cursor), `/sync-logs/{id}`, `/sync-logs/sources`, `/analytics/summary`, `/analytics/sources`, `/failures`, `/monitors`, `/users/me/preferences`, `/health`, `/version`.

SPA serving: `GET /app` and `GET /app/{path:path}` return `app/static/app/index.html` (no cache); assets under `/static/app/*` with content hashes (long cache). After cut-over `GET /` returns the same.

## 6. Frontend Architecture

- `frontend/` — Vite 6, React 19, TypeScript strict, React Router 7, TanStack Query 5, Recharts 2, Tailwind CSS 4, `date-fns`. Tests: Vitest + Testing Library + MSW for API mocks.
- Build output → `app/static/app/` (gitignored; produced in Docker Node stage and by `npm run build` locally).
- API client: typed fetch wrapper with `credentials: 'include'`; 401 → redirect to `/login?return_url=`.
- Theme: read `data-theme` set by the server-rendered shell; SPA `index.html` includes the same inline theme bootstrap; toggle PATCHes `/users/me/preferences`.
- Polling: liveness pill uses TanStack Query `refetchInterval = interval_seconds`; overview data every 60 s. (SSE is M13.)

## 7. Edge Cases

- **No synthetic config row / disabled** → `status: "disabled"`, uptime fields `null` (AC-007).
- **Uptime with < 2 checks in window** → `uptime_24h_pct: null`, pill shows "—".
- **Source with a monitor but no syncs** → `last_status: "never"`, `is_stale` per monitor rule.
- **Sync with 50k files** → detail fetch is on expand only; list virtualised; file list capped server-side? No — `SyncLogDetail` already returns all; virtualise client-side.
- **Ambiguous media paths** (`Photos/2026/IMG_1.jpg`) → no item; `Movies/movie_112.mkv` (no year) → movie with `year: null`, title `movie 112`.
- **Same episode from two sources** → single item; first sighting wins.
- **Title cleanup collisions** (`Dune (1984)` vs `Dune (2021)`) → distinct by year.
- **Timezones** → API returns UTC ISO-8601; SPA renders in the browser's local zone; day grouping uses local dates.
- **Legacy `?tab=analytics` links** → `/app/trends` redirect.
- **Viewer role** → all SPA pages readable; settings menu item hidden for viewers (`/settings` is operator+).

## 8. Screenshot Checkpoints

`tests/screenshots/insight-ui/`: step-01-overview, step-02-failure-drilldown, step-03-trends, step-04-media, step-05-uptime, step-06-mobile. Captured by the rewritten Playwright tests (`tests/e2e/test_insight_ui.py`).

## 9. Out of Scope (this milestone)

Rebuilding login/settings/admin in React; SSE live updates (M13); monitor CRUD UI (M12); PWA (M15); global search (M13).
