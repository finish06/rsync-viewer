# Plan: Overview v2 — exceptions first

**Spec:** specs/overview-v2.md · **UX:** specs/ux/overview-v2-ux.md · **Branch:** `feature/overview-v2` · **Release:** v2.19.0 (`feat:` → minor)

## Tasks
| # | Task | Files | AC |
|---|------|-------|----|
| T1 | `cadence.ts`: `nextDue(source)` → `{dueAt, overdueHours} \| null` (monitor interval first, else median active-day gap) + unit tests | `frontend/src/features/overview/cadence.ts` | AC-003 |
| T2 | `AttentionStrip.tsx`: calm line (sources + liveness) vs problem cards (streak, overdue, link) | `frontend/src/features/overview/AttentionStrip.tsx` | AC-001, AC-002 |
| T3 | `SourceRow.tsx` compact healthy row; `SourceGrid` splits problems→cards / healthy→rows; keep inactive toggle | `SourceRow.tsx`, `SourceGrid.tsx`, `SourceCard.tsx` (declutter) | AC-002, AC-005, AC-006 |
| T4 | `VolumeTrend.tsx`: bytes/day summed across sources, ambient Recharts area in the strip | `VolumeTrend.tsx`, `OverviewPage.tsx` | AC-004 |
| T5 | Declutter helpers: plural(), byte floor | `SourceCard.tsx`, `SourceRow.tsx` | AC-005 |
| T6 | Tests: component (strip both states, row chips, cadence table, volume sums, declutter), OverviewPage integration; E2E `test_insight_ui.py` updated (`source-row` for healthy) + screenshots | `*.test.tsx`, `tests/e2e/test_insight_ui.py` | all |

## Test strategy
RED first: cadence unit table; strip renders calm vs problems from MSW health fixtures; healthy row shows chip/sparkline/link; volume chart totals; existing SourceGrid/OverviewPage tests updated to the new split.

## Risks
- E2E `test_insight_ui.py` TC-001 relies on `source-card` for a healthy source → moves to `source-row` (AC-006).
- Inferred cadence on sparse history can mislead — omit the chip rather than guess (spec edge case).
