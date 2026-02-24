# Project Learnings — rsync-viewer

> **Tier 3: Project-Specific Knowledge**
> Generated from `.add/learnings.json` — do not edit directly.
> Agents read JSON for filtering; this file is for human review.

## Anti-Patterns
- **[high] CSRF middleware breaks existing test fixtures — plan ahead** (L-008, 2026-02-23)
  Adding CSRF validation middleware retroactively requires updating ALL test client fixtures to include csrf_token cookie and X-CSRF-Token header. Tests that need to verify CSRF rejection must create a separate client without tokens. Always plan for test fixture impact when adding cross-cutting middleware.

- **[high] DB schema drift: model changes need manual ALTER TABLE on live DB** (L-011, 2026-02-23)
  SQLModel/Alembic create_all() handles test DBs but the live PostgreSQL DB requires explicit ALTER TABLE for new columns. When adding columns to models (e.g. exit_code on sync_logs), also apply the migration to the running DB. Consider adding Alembic migrations to prevent this class of issue.

## Architecture
- **[low] Jinja2 filters taking full model objects keeps templates clean** (L-002, 2026-02-20)
  format_rate(sync) accessing sync.bytes_received, sync.start_time, sync.end_time, sync.is_dry_run internally is cleaner than passing individual args. Template usage stays simple: {{ sync | format_rate }}. Apply this pattern for future computed display values.

## Technical
- **[high] slowapi rate limiting: headers_enabled and middleware interaction** (L-007, 2026-02-23)
  slowapi defaults headers_enabled=False — set True in Limiter constructor for X-RateLimit-* headers. Using @limiter.limit() decorator with headers_enabled=True requires a Response parameter on the endpoint. SlowAPIMiddleware with default_limits is simpler — applies limits globally without per-route decorators. Don't mix both approaches.

- **[medium] Webhook service TDD cycle: clean RED→GREEN→REFACTOR in one away session** (L-004, 2026-02-21)
  ACs covered: AC-001 through AC-011 (except AC-007 UI). RED: 27 tests across 3 files (unit API, unit dispatcher, integration). GREEN: all passed first implementation attempt. Blockers: none. Mock pattern for httpx.AsyncClient with AsyncMock __aenter__/__aexit__ works well for testing async context managers. Proactively dropping/recreating test DB tables before RED phase avoided schema mismatch issues seen in failure-detection cycle.

- **[medium] httpx AsyncClient mock pattern for webhook testing** (L-005, 2026-02-21)
  Patch 'module.httpx.AsyncClient' and set mock_client.__aenter__ = AsyncMock(return_value=mock_client), __aexit__ = AsyncMock(return_value=False). For capture tests, replace mock_client.post with a plain async function that captures args. Patch asyncio.sleep with AsyncMock to skip retry delays. This pattern is reusable for any service using httpx async context managers.

## Process
- **[medium] Retro 2: ruff format drift and E2E CI exclusion** (L-012, 2026-02-23)
  Period 2026-02-20→23 covered M2-M5 (132→350 tests, 93% coverage). Two process issues: (1) ruff format drift accumulated silently across 9 files — always run ruff format before committing; (2) Playwright E2E adds CI complexity at alpha maturity with marginal gain — defer to beta, keep local-only. Workflow otherwise solid — TDD cycle and quality gates are reliable.

- **[medium] Cycle 4 complete: M4 Analytics — 3 features, 30+30 tests, 93% coverage** (L-010, 2026-02-23)
  Cycle 4 delivered Statistics API, Data Export, and Dashboard Charts. 30 unit tests + 30 Playwright E2E tests. All 10 analytics ACs verified. Key findings: (1) live DB schema drift caused 500s — exit_code column was in the model but missing from DB, needed ALTER TABLE; (2) CSV StreamingResponse with Content-Disposition: attachment triggers Playwright download errors, use page.request.get() instead of page.goto(); (3) module-wide pytestmark=pytest.mark.asyncio is unnecessary with asyncio_mode=auto and generates warnings on sync tests. M4 at 8/9 success criteria — only response time benchmark remains.

- **[medium] Cycle 3 complete: M4 Performance Foundations — 3 features, 25 new tests** (L-009, 2026-02-23)
  Cycle 3 delivered Database Indexing (6 composite/individual indexes), Query Optimization (lazy file lists, connection pool config), and Cursor Pagination (keyset with offset fallback). 25 new tests, 319 total passing. Also ran deprecation cleanup (utc_now() helper replacing 61 datetime.utcnow() calls, Starlette TemplateResponse fix). Key insight: naive vs tz-aware datetime mismatch with PostgreSQL requires a centralized utc_now() helper returning naive UTC. Production indexes created manually with CREATE INDEX CONCURRENTLY.

- **[medium] Cycle 2 complete: M3 Reliability — 3 features, 57 new tests, 92% coverage** (L-006, 2026-02-23)
  Cycle 2 delivered Structured Logging (15 tests), Error Handling (12 tests), and Security Hardening (30 tests). All 34 ACs verified. Total suite: 294 tests at 92% coverage. Key learnings: slowapi requires headers_enabled=True explicitly; CSRF middleware must be accounted for in all test fixtures; Python 3.13 venv upgrade was needed for dict|None syntax. M3 is the beta promotion gate — all criteria met.

- **[medium] Cycle 1 complete: 2 dashboard features in 1 day** (L-001, 2026-02-20)
  Cycle 1 delivered Date Range Quick Select and Average Transfer Rate. Both followed spec→plan→implement→test flow. 132 tests passing, 92% coverage. Reviewer caught JS duplication in quick-select — extracting shared functions early saves rework. format_rate filter pattern mirrors format_bytes, confirming the Jinja2 filter approach scales well.

- **[medium] Promoted POC → Alpha: evidence score 9/10** (L-003, 2026-02-20)
  M1 milestone complete with all 6 features shipped. Promotion backed by: 6 specs, 92% coverage, CI pipeline, 3 PRs merged, conventional commits (15/20), 3 release tags, TDD evidence. Only gap: branch protection not enforced on GitHub (only declared in config). Next target: Beta requires full TDD on all paths and 30+ days stability.

---
*12 entries. Last updated: 2026-02-23. Source: .add/learnings.json*
