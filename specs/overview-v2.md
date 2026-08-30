# Spec: Overview v2 — exceptions first

## 1. Overview

Iteration on the M16 Overview (specs/insight-ui.md) from user feedback
(2026-08-30): the page is "better, not perfect". Product decisions taken in
the interview:
- the first glance must answer **"is anything broken?"**;
- problem sources deserve cards, healthy sources a **compact row**;
- production runs **1–3 real sources**, so richness beats density;
- missing: **when the next sync is due** and a **volume trend**; otherwise
  **declutter** (no "45 B" noise, no "1 syncs").

### User Story
As a homelab operator with a couple of rsync jobs, I open the Overview and
want one calm line telling me everything is fine — or loud, specific cards
telling me exactly what is broken, since when, and what was expected.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | An **attention strip** leads the page: when every source is healthy and the synthetic check is not failing, it shows a single calm line ("All N sources healthy", with the liveness state alongside). When anything is failed/stale/liveness-failing it shows loud per-problem cards. | Must |
| AC-002 | **Problem sources** (failed or stale) render as cards carrying: status, last-sync relative time, failure streak, and how overdue the sync is; the card links to the filtered Transfers page. **Healthy sources** render as compact rows: status dot · name · "synced X ago" · next-due chip · sparkline · window totals — the row links like the card did. | Must |
| AC-003 | **Next sync due**: when a monitor defines `expected_interval_hours`, due = `last_sync_at + interval`; otherwise the cadence is inferred from the 14-day history (median gap between active days); if neither is known the chip is omitted. Display "due in ~Xh" (healthy) or "overdue by Xh". | Must |
| AC-004 | A **volume trend** — bytes/day summed across sources over the window — is visible on the Overview without opening Trends (computed client-side from data already fetched). | Must |
| AC-005 | **Declutter**: correct singular/plural ("1 sync"), failure counts hidden when zero, byte totals under 1 KB shown as "—", healthy rows carry no redundant status words. | Must |
| AC-007 | **New-this-week diary** (iteration 2026-08-30): the widget lists the trailing 7 days newest-first as day rows ("Friday · …"). Within a day, episodes of one show collapse to a single entry with a count and episode range ("Severance ×2 · S02E05–06"); movies show "Title (Year)". Watch-list tone: no source names, sizes, or sync times. | Must |
| AC-008 | Days without arrivals render greyed ("Wednesday — nothing new") so the 7-day rhythm stays visible; a week with no arrivals at all keeps the single "Nothing new this week" note. | Must |
| AC-009 | At most 4 titles render per day; overflow becomes "+N more" linking to the Media page. The aggregate counts line is removed — the diary is the content. | Must |
| AC-006 | Existing behaviours are preserved: empty-state call to action, inactive-source toggle, `data-status` attributes for tests, links to `/app/transfers?source=…`. E2E selectors move from `source-card` (now problems only) to `source-row` for healthy sources. | Must |

## 3. User Test Cases
- **TC-001** All sources healthy → calm strip line, no cards, healthy rows with next-due chips, volume chart visible. (screenshot `step-01-all-healthy`)
- **TC-002** One source failing with a streak → attention card names it, shows "3 in a row" and overdue time; healthy sources stay as rows below. (screenshot `step-02-failure`)
- **TC-003** A source with a monitor at 24 h that last synced 30 h ago → "overdue by ~6h" on its card/row.
- **TC-004** A fresh instance → unchanged "Waiting for your first sync" call to action.
- **TC-005** A week with arrivals on three days → three normal day rows (newest first) + four greyed rows; a show that received two episodes on Friday shows once with "×2 · S02E05–06". (screenshot `step-03-diary`)

## 4. Data
No backend changes: `GET /api/v1/sources/health?days=14` already provides
`expected_interval_hours`, `is_stale`, `consecutive_failures`, `daily[]`
(syncs, failures, bytes per day); the synthetic status comes from the existing
liveness query. Cadence inference and the volume series are client-side.

## 5. Edge Cases
- Single active day in the window → no inferred cadence → no chip.
- `last_sync_at` null (never synced) → no chip, "never synced" row/card.
- All sources inactive in the window → existing empty message + toggle.
- Synthetic check disabled → strip reflects sources only.

## 6. Screenshot Checkpoints
`tests/screenshots/overview-v2/step-01-all-healthy.png`, `step-02-failure.png`.
