# UX Design: Insight UI

**Spec:** specs/insight-ui.md
**Status:** DRAFT — pending human sign-off (generated 2026-08-29 from the goal statement; no interview held)
**Iterations:** 1

Design intent, in the user's words: *show me what was sent in a condensed manner with the ability to dive into details; transfers over time; new shows, new movies; synthetic monitoring must be obviously "up"; settings are used sometimes, not often.*

Design principles derived from that:
1. **Status before data.** Liveness is the first thing on every page (header pill), then per-source health, then activity.
2. **Condense, then expand in place.** Every list is a rollup (day → source → sync → files). Expansion is inline; navigation is only for changing *question*, not for seeing detail.
3. **Titles, not paths.** Media is shown as shows/movies; paths are one expansion away.
4. **Settings are a menu, not a tab.**

## Screens

### Global shell (all pages)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ◉ Rsync Viewer   Overview  Transfers  Trends  Media  Uptime      ● UP 99.8% │
│                                                                  checked 2m │
│                                                        [☾] [⚙ ▾ Settings…]  │
└──────────────────────────────────────────────────────────────────────────────┘
```
- Liveness pill (right): green `● UP 99.8% · checked 2m ago`, red `● DOWN · failing 3 checks`, grey `○ Synthetic check off → enable`. Click → Uptime page.
- `⚙ ▾` menu: Settings (operator+), Admin users (admin), API keys, Changelog, Log out. Viewers see API keys, Changelog, Log out only.
- Active nav item underlined with the accent colour; nav collapses to a bottom bar on mobile.

### Screen 1: Overview (`/app`) — "Is everything OK, and what happened?"

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  SOURCES                                                     last 14 days    │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ │
│  │ ● movies       │ │ ● tv           │ │ ▲ photos       │ │ ✕ nas-backup   │ │
│  │ synced 12m ago │ │ synced 1h ago  │ │ STALE · 3d ago │ │ FAILED 40m ago │ │
│  │ ▁▂▃▅▂▁▃▆▂▁▂▄▃▂ │ │ ▂▂▃▂▂▂▃▂▂▂▂▂▃▂ │ │ ▃▃▂▁▁▁▁▁▁▁▁▁▁▁ │ │ ▂▂▂▂▂▂▂▂▂▂▂▂██ │ │
│  │ 14 syncs · 0 ✕ │ │ 28 syncs · 0 ✕ │ │ 3 syncs · 0 ✕  │ │ 14 syncs · 2 ✕ │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘ │
│                                                                              │
│  NEW THIS WEEK                                   ACTIVITY · last 7 days      │
│  ┌──────────────────────────────┐   ┌──────────────────────────────────────┐ │
│  │ 🎬 3 movies   📺 2 shows      │   │ ▸ Today      6 syncs · 0 ✕ · 42.1 GB │ │
│  │    Severance S02E03           │   │ ▾ Yesterday  9 syncs · 1 ✕ · 18.7 GB │ │
│  │    The Polar Express (2004)   │   │    ✕ nas-backup 23:10  3m  0 B  #11  │ │
│  │    …  → Media                 │   │    ● movies     21:00  4m  6.2 GB    │ │
│  └──────────────────────────────┘   │    ● tv         20:30  1m  1.1 GB    │ │
│                                     │ ▸ Aug 27     7 syncs · 0 ✕ · 22.0 GB │ │
│                                     │ ▸ Aug 26     … (5 more days)         │ │
│                                     └──────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```
- Card colour: green ok · red failed (last sync non-zero exit) · amber stale (monitor interval exceeded) · grey never. Sparkline bars = syncs/day; red bar segments = failures. Click card → `/app/transfers?source=…`.
- Activity rows expand inline (▾) to that day's syncs; clicking a sync row expands again to files/failure detail (same component as Transfers).
- "New this week" shows counts and up to 5 titles; link to Media.

### Screen 2: Transfers (`/app/transfers`) — "What was sent?"

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Source [All ▾]   Range [7d] 30d 90d Custom   Status [All] Failed   ☐ dry-runs│
│──────────────────────────────────────────────────────────────────────────────│
│  ▾ Yesterday · 9 syncs · 1 failed · 18.7 GB · 1,204 files                    │
│    ▾ nas-backup · 2 syncs · 1 failed                                          │
│      ✕ 23:10  3m 12s   0 B      0 files   exit 11                            │
│        ┌────────────────────────────────────────────────────────────────┐    │
│        │ rsync: write failed on "/backup/Videos/Movies/big_movie.mkv":  │    │
│        │ No space left on device (28)                                   │    │
│        │ rsync error: error in file IO (code 11) at receiver.c(393)     │    │
│        │ ── files (0) ──                                                │    │
│        └────────────────────────────────────────────────────────────────┘    │
│      ● 11:10  2m 40s   4.1 GB   312 files  speedup 1.02                      │
│    ▸ movies · 3 syncs · 6.2 GB                                                │
│    ▸ tv · 4 syncs · 1.1 GB                                                    │
│  ▸ Aug 27 · 7 syncs · 22.0 GB                                                 │
│  ▸ Aug 26 · …                                                                 │
│                                     … infinite scroll …                       │
└──────────────────────────────────────────────────────────────────────────────┘
```
- Three levels: day → source → sync; sync expands to detail (raw tail on failure, file list virtualised, copy-path on hover).
- Filters mirror the URL (`?source=&range=&status=&from=&to=`).

### Screen 3: Trends (`/app/trends`) — "How is it changing?"

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Period [Daily ▾]   Range 7d [30d] 90d Custom   Source [All ▾]               │
│  ┌─── Bytes transferred ─────────────┐ ┌─── Files transferred ─────────────┐ │
│  │       ▂▃▅▇▅▃▂▃▆▇▆▃▂▂▃▅           │ │       ▂▂▃▄▃▂▂▃▅▄▃▂▂▂▃▄           │ │
│  └───────────────────────────────────┘ └───────────────────────────────────┘ │
│  ┌─── Duration (avg) ────────────────┐ ┌─── Success / failure ─────────────┐ │
│  │       ▂▂▃▃▃▂▂▃▄▃▃▂▂▂▃▃           │ │       ████████████▓███████        │ │
│  └───────────────────────────────────┘ └───────────────────────────────────┘ │
│  SOURCES                                                                     │
│  source      syncs   success   avg duration   avg bytes    last sync          │
│  movies        42     100%      3m 10s         5.9 GB       12m ago   ▸       │
│  nas-backup    14      86%      2m 55s         3.8 GB       40m ago   ▸       │
└──────────────────────────────────────────────────────────────────────────────┘
```
- Shared hover cursor across the four charts; click a bar → Transfers filtered to that day. Click a source row → charts filter to it (row highlighted; "× clear").

### Screen 4: Media (`/app/media`) — "What's new?"

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  New in the last [7 days ▾]         🎬 3 movies   📺 2 shows · 5 episodes     │
│  ┌── SHOWS ───────────────────────────┐ ┌── MOVIES ─────────────────────────┐ │
│  │ Severance (2022)        3 new      │ │ The Polar Express (2004)          │ │
│  │   S02E01 · S02E02 · S02E03  ▸      │ │   Aug 27 · movies · 8.2 GB   ▸    │ │
│  │ Slow Horses (2022)      2 new      │ │ The Noel Diary (2022)             │ │
│  │   S04E05 · S04E06            ▸     │ │   Aug 26 · movies · 6.1 GB   ▸    │ │
│  └────────────────────────────────────┘ │ The Perfect Christmas Present     │ │
│                                         │ (2017)  Aug 26 · movies      ▸    │ │
│                                         └───────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```
- ▸ opens the originating transfer (Transfers page, sync expanded, file highlighted).

### Screen 5: Uptime (`/app/uptime`) — "Is the pipeline alive?"

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ● Synthetic check PASSING · every 5 min · last 2m ago · 143 ms              │
│  24h uptime  99.8%      7d uptime  99.6%      checks (24h)  288 · 1 failed   │
│  ┌─── last 100 checks (newest right) ───────────────────────────────────────┐│
│  │ ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■□■■■■■■■■■ ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│  ┌─── latency (ms) ─────────────────────────────────────────────────────────┐│
│  │        ▂▂▂▃▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂█▂▂▂▂▂▂▂▂▂▂                                   ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│  Recent failures                                                             │
│  Aug 28 03:15   POST /sync-logs → 502 Bad Gateway                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

## State Matrix

| State | Behaviour | Notes |
|-------|-----------|-------|
| Loading | Skeleton cards/rows in place; pill shows "checking…" | never a blank page |
| Empty (no syncs ever) | Overview shows "Waiting for your first sync" + monitoring-setup CTA (operator+) / "ask an operator" (viewer) | AC-026 |
| Empty (filtered) | "No transfers match" with a "clear filters" action | |
| Error (API 5xx) | Inline error card with retry; other panels unaffected | per-panel queries |
| Auth expired (401) | Redirect to `/login?return_url=` | |
| Synthetic disabled | Grey pill with settings link; Uptime page explains how to enable | AC-007 |
| Success | As drawn | |
| Mobile (≤ 640 px) | Nav → bottom bar; cards 1-col; activity strip full width; charts 1-col | AC-027 |

## Flow

```
/login ──► /app (Overview) ──card──► /app/transfers?source=X ──row──► inline detail
                │                       ▲
                ├──activity row──► inline day expansion ──sync──► inline detail
                ├──"New this week"──► /app/media ──▸──► /app/transfers?sync=ID (expanded)
                ├──pill──► /app/uptime
                └──Trends nav──► /app/trends ──bar click──► /app/transfers?from=D&to=D
⚙ menu ──► /settings, /admin/users, /htmx api keys page (server-rendered, unchanged)
```

## Key decisions (call out if you disagree)

1. **Overview is source-first, not log-first** — the cards answer "is everything OK" before any list is read.
2. **Detail is always inline** (expand), never a modal or a page: fewer clicks, no lost context.
3. **Media derived at ingest, stored in a table** — makes "new this week" a cheap query and survives log retention.
4. **Settings live behind a menu** — matches "used sometimes, not often".
5. **Polling, not SSE, for liveness** — SSE is M13; the pill polls at the check interval.
6. **Legacy dashboard removed at cut-over**, not kept side-by-side — one UI to maintain.

## Spec impact

None beyond the spec as written. If sign-off changes the navigation set or the media rules, update AC-016 and AC-023.
