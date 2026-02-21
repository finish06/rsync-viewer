# Project Learnings — rsync-viewer

> **Tier 3: Project-Specific Knowledge**
> Generated from `.add/learnings.json` — do not edit directly.
> Agents read JSON for filtering; this file is for human review.

## Architecture
- **[low] Jinja2 filters taking full model objects keeps templates clean** (L-002, 2026-02-20)
  format_rate(sync) accessing sync.bytes_received, sync.start_time, sync.end_time, sync.is_dry_run internally is cleaner than passing individual args. Template usage stays simple: {{ sync | format_rate }}. Apply this pattern for future computed display values.

## Process
- **[medium] Cycle 1 complete: 2 dashboard features in 1 day** (L-001, 2026-02-20)
  Cycle 1 delivered Date Range Quick Select and Average Transfer Rate. Both followed spec→plan→implement→test flow. 132 tests passing, 92% coverage. Reviewer caught JS duplication in quick-select — extracting shared functions early saves rework. format_rate filter pattern mirrors format_bytes, confirming the Jinja2 filter approach scales well.

- **[medium] Promoted POC → Alpha: evidence score 9/10** (L-003, 2026-02-20)
  M1 milestone complete with all 6 features shipped. Promotion backed by: 6 specs, 92% coverage, CI pipeline, 3 PRs merged, conventional commits (15/20), 3 release tags, TDD evidence. Only gap: branch protection not enforced on GitHub (only declared in config). Next target: Beta requires full TDD on all paths and 30+ days stability.

## Technical
- **[medium] Webhook service TDD cycle: clean RED→GREEN→REFACTOR in one away session** (L-004, 2026-02-21)
  ACs covered: AC-001 through AC-011 (except AC-007 UI). RED: 27 tests across 3 files (unit API, unit dispatcher, integration). GREEN: all passed first implementation attempt. Blockers: none. Mock pattern for httpx.AsyncClient with AsyncMock __aenter__/__aexit__ works well for testing async context managers. Proactively dropping/recreating test DB tables before RED phase avoided schema mismatch issues seen in failure-detection cycle.

- **[medium] httpx AsyncClient mock pattern for webhook testing** (L-005, 2026-02-21)
  Patch 'module.httpx.AsyncClient' and set mock_client.__aenter__ = AsyncMock(return_value=mock_client), __aexit__ = AsyncMock(return_value=False). For capture tests, replace mock_client.post with a plain async function that captures args. Patch asyncio.sleep with AsyncMock to skip retry delays. This pattern is reusable for any service using httpx async context managers.

## Technical Discoveries

- 2026-02-19: RsyncParser uses regex patterns to extract transfer stats from raw rsync output. Supports unit parsing for B, K, M, G, T, P suffixes. Source: app/services/rsync_parser.py
- 2026-02-19: Database uses SQLModel with JSONB columns for file_list and source_names fields. UUID primary keys throughout. Source: app/models/sync_log.py
- 2026-02-19: API authentication uses X-API-Key header with hashed key lookup via ApiKey model. Source: app/api/deps.py
- 2026-02-19: Tests use async httpx.AsyncClient with transaction-rolled-back database sessions for isolation. Source: tests/conftest.py

## Architecture Decisions

- 2026-02-19: Chose HTMX over React/Vue for frontend — server-rendered with small dynamic updates, keeps stack simple for homelab.
- 2026-02-19: Chose SQLModel over raw SQLAlchemy — Pydantic integration reduces boilerplate for FastAPI.

## What Worked

- Fixture-based test data with multiple rsync output variants provides good parser coverage.
- Docker Compose with separate dev/prod/test configurations keeps environments clean.
- Spec-driven flow with "default" answers for non-critical questions keeps interviews fast.

---
*5 JSON entries + legacy discoveries. Last updated: 2026-02-21. Source: .add/learnings.json*
