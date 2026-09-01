# Plan: CSV export from the UI

**Spec:** specs/csv-export-ui.md · **Branch:** `feature/csv-export-ui` · **Release:** v2.23.0 (`feat:` → minor)

## Tasks
| # | Task | Files | AC |
|---|------|-------|----|
| T1 | `source` becomes `Query(None)` list; filter with `col(...).in_(...)`, keeping single-value and synthetic semantics | `app/api/endpoints/analytics.py` | AC-001–003 |
| T2 | `ExportPanel` component: source checkboxes (+ All), synthetic toggle, date range prefilled from page filters, format select, cap note, disabled-empty state | `frontend/src/features/transfers/ExportPanel.tsx` | AC-004, AC-006, AC-007 |
| T3 | `buildExportUrl(options)` pure helper (repeated source params, synthetic, dates, format) + download trigger via a hidden anchor | `frontend/src/features/transfers/exportUrl.ts` | AC-005, AC-006 |
| T4 | Wire the Export button into the Transfers filter bar | `frontend/src/features/transfers/TransfersPage.tsx` | AC-004 |
| T5 | Tests: backend multi-source/synthetic/date combos; frontend url-builder table + panel interaction (select subset, toggle synthetic, disabled state, download call); E2E download + screenshot | `tests/test_analytics.py`, `frontend/src/features/transfers/*.test.tsx`, `tests/e2e/` | all |
| T6 | CHANGELOG 2.23.0 | `CHANGELOG.md` | — |

## Test strategy
RED first on both stacks. Frontend uses a pure URL builder so query-string
assertions do not depend on the DOM; the panel test asserts the builder's
output is what the download uses. E2E performs a real download via Playwright's
`expect_download` and screenshots the open panel.

## Risks
- Downloads in E2E need `accept_downloads` context — the fixture creates its own context; use `page.expect_download()` which enables it per-context in Playwright ≥1.40, else assert the anchor href.
