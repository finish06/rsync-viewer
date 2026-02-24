# Project Learnings — rsync-viewer

> **Tier 3: Project-Specific Knowledge**
> Generated from `.add/learnings.json` — do not edit directly.
> Agents read JSON for filtering; this file is for human review.

## Anti-Patterns

- **[high] DB schema drift: model changes need manual ALTER TABLE on live DB** (L-011, 2026-02-23)
  SQLModel/Alembic create_all() handles test DBs but the live PostgreSQL DB requires explicit ALTER TABLE for new columns. When adding columns to models (e.g. exit_code on sync_logs), also apply the migration to the running DB. Consider adding Alembic migrations to prevent this class of issue.

## Technical

- **[medium] Webhook service TDD cycle: clean RED→GREEN→REFACTOR in one away session** (L-004, 2026-02-21)
  ACs covered: AC-001 through AC-011 (except AC-007 UI). RED: 27 tests across 3 files. GREEN: all passed first attempt. Mock pattern for httpx.AsyncClient with AsyncMock __aenter__/__aexit__ works well.

## Architecture

- **[low] Jinja2 filters taking full model objects keeps templates clean** (L-002, 2026-02-20)
  format_rate(sync) accessing sync fields internally is cleaner than passing individual args. Template usage stays simple: {{ sync | format_rate }}.

## Process

- **[high] Retro 3: CI must pass before PR, drop Playwright, promote to Beta** (L-015, 2026-02-24)
  Three agreed changes: (1) verify CI passes before creating PRs; (2) mount project root in docker-compose.dev.yml; (3) drop Playwright e2e entirely. Promoted Alpha→Beta with 7/7 evidence criteria met.

- **[medium] Cycle 6 complete: M6 Observability — docs + Grafana in 1 day** (L-013, 2026-02-24)
  6 documentation files and 2 Grafana dashboard templates, verified by 27 new tests. TDD for documentation is lightweight but effective. M6 complete: 8/8 success criteria met across 2 cycles.

- **[medium] Retro 2: ruff format drift and E2E CI exclusion** (L-012, 2026-02-23)
  Always run ruff format before committing. TDD cycle and quality gates are reliable.

- **[medium] Cycle 4 complete: M4 Analytics** (L-010, 2026-02-23)
  Statistics API, Data Export, Dashboard Charts. 60 tests. All 10 ACs verified.

- **[medium] Cycle 3 complete: M4 Performance Foundations** (L-009, 2026-02-23)
  Database Indexing, Query Optimization, Cursor Pagination. 25 new tests. Key: centralized utc_now() helper for naive UTC datetimes.

- **[medium] Cycle 2 complete: M3 Reliability** (L-006, 2026-02-23)
  Structured Logging, Error Handling, Security Hardening. 57 new tests, 92% coverage.

- **[medium] Promoted POC → Alpha: evidence score 9/10** (L-003, 2026-02-20)
  M1 complete with 6 features. 92% coverage, CI pipeline, conventional commits, TDD evidence.

- **[medium] Cycle 1 complete: 2 dashboard features in 1 day** (L-001, 2026-02-20)
  Date Range Quick Select and Average Transfer Rate. 132 tests, 92% coverage.

---
*11 entries. Last updated: 2026-02-24. Source: .add/learnings.json*
*4 workstation-scope entries promoted to ~/.claude/add/library.json (WL-001 through WL-004)*
