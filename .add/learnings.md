# Project Learnings — rsync-viewer

> **Tier 3: Project-Specific Knowledge**
>
> This file is maintained automatically by ADD agents. Entries are added at checkpoints
> (after verify, TDD cycles, deployments, away sessions) and reviewed during retrospectives.
>
> This is one of three knowledge tiers agents read before starting work:
> 1. **Tier 1: Plugin-Global** (`knowledge/global.md`) — universal ADD best practices
> 2. **Tier 2: User-Local** (`~/.claude/add/library.md`) — your cross-project wisdom
> 3. **Tier 3: Project-Specific** (this file) — discoveries specific to this project
>
> **Agents:** Read ALL three tiers before starting any task.
> **Humans:** Review with `/add:retro --agent-summary` or during full `/add:retro`.

## Technical Discoveries
<!-- Things learned about the tech stack, libraries, APIs, infrastructure -->
<!-- Format: - {date}: {discovery}. Source: {how we learned this}. -->

- 2026-02-19: RsyncParser uses regex patterns to extract transfer stats from raw rsync output. Supports unit parsing for B, K, M, G, T, P suffixes. Source: app/services/rsync_parser.py
- 2026-02-19: Database uses SQLModel with JSONB columns for file_list and source_names fields. UUID primary keys throughout. Source: app/models/sync_log.py
- 2026-02-19: API authentication uses X-API-Key header with hashed key lookup via ApiKey model. Source: app/api/deps.py
- 2026-02-19: Tests use async httpx.AsyncClient with transaction-rolled-back database sessions for isolation. Source: tests/conftest.py

## Architecture Decisions
<!-- Decisions made and their rationale -->
<!-- Format: - {date}: Chose {X} over {Y} because {reason}. -->

- 2026-02-19: Chose HTMX over React/Vue for frontend because the app is primarily server-rendered with small dynamic updates — HTMX keeps the stack simple for a homelab project.
- 2026-02-19: Chose SQLModel over raw SQLAlchemy for ORM because it provides Pydantic integration out of the box, reducing boilerplate for FastAPI request/response handling.
- 2026-02-20: Jinja2 filters taking full model objects (e.g., format_rate(sync)) keeps templates clean and consolidates edge-case logic. Apply this pattern for future computed display values.

## What Worked
<!-- Patterns, approaches, tools that proved effective -->

- Fixture-based test data with multiple rsync output variants (basic, dry run, terabytes, kilobytes, empty, malformed) provides good parser coverage.
- Docker Compose with separate dev/prod/test configurations keeps environments clean.

## What Didn't Work
<!-- Patterns, approaches, tools that caused problems -->

## Agent Checkpoints
<!-- Automatic entries from verification, TDD cycles, deploys, away sessions -->
<!-- These are processed and archived during /add:retro -->

### Cycle 1 Complete (2026-02-20)
- **Features:** Date Range Quick Select, Average Transfer Rate
- **Duration:** 1 day
- **Tests:** 132 passing, 92% coverage
- **Outcome:** Both features specced, planned, implemented, tested, committed, and pushed
- **Learning:** Reviewer caught JS duplication in quick-select — extracting shared functions early saves rework. format_rate filter mirrors format_bytes, confirming the Jinja2 filter approach scales well.

## Profile Update Candidates
<!-- Cross-project patterns flagged for promotion to ~/.claude/add/profile.md -->
<!-- Only promoted during /add:retro with human confirmation -->
