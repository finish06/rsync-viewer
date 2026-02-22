# Implementation Plan: Discord Integration

**Spec Version**: 0.1.0
**Created**: 2026-02-21
**Team Size**: Solo
**Estimated Duration**: 1 day

## Overview

Extend the webhook service with Discord-specific rich embed formatting, a generic `WebhookOptions` table for type-specific configuration, per-source filtering, Discord URL validation, a test message endpoint, and Discord rate limit handling.

## Objectives

- Rich Discord embeds with configurable color, username, avatar, footer
- Per-source webhook filtering via `source_filters`
- Generic `WebhookOptions` model (JSONB) extensible to future integrations
- Discord URL validation and test message endpoint
- Discord 429 rate limit respect

## Success Criteria

- All 13 acceptance criteria implemented and tested
- Code coverage >= 80%
- All quality gates passing (ruff, pytest)
- Generic webhooks continue working unchanged (AC-011)

## Implementation Phases

### Phase 1: Data Layer (models + schemas + migration)

Extend `WebhookEndpoint`, create `WebhookOptions`, update schemas.

| Task ID | Description | ACs | Effort | Dependencies |
|---------|-------------|-----|--------|--------------|
| TASK-001 | Add `webhook_type` and `source_filters` columns to WebhookEndpoint model | AC-012 | 20min | — |
| TASK-002 | Create `WebhookOptions` model with JSONB `options` column, FK to webhook_endpoints | AC-013 | 20min | — |
| TASK-003 | Update `WebhookCreate` schema: add `webhook_type`, `source_filters`, `options` fields | AC-005, AC-006, AC-008 | 30min | TASK-001, TASK-002 |
| TASK-004 | Update `WebhookUpdate` and `WebhookRead` schemas to include new fields | AC-005, AC-006 | 20min | TASK-003 |
| TASK-005 | Add Discord URL validator (regex for discord.com/discordapp.com webhook URLs) | AC-008 | 15min | TASK-003 |
| TASK-006 | Register WebhookOptions model in conftest.py and main.py | AC-013 | 10min | TASK-002 |

**Phase Duration**: ~2 hours

### Phase 2: Dispatcher Logic

Extend `dispatch_webhooks` with source filtering and Discord payload formatting.

| Task ID | Description | ACs | Effort | Dependencies |
|---------|-------------|-----|--------|--------------|
| TASK-007 | Add source filter check in dispatcher — skip webhooks where source not in `source_filters` | AC-006, AC-007 | 20min | TASK-001 |
| TASK-008 | Create `_build_discord_payload()` — format FailureEvent as Discord embed with fields, color, username, avatar, footer, dashboard link | AC-001, AC-002, AC-003, AC-004, AC-005 | 45min | TASK-002 |
| TASK-009 | Update `dispatch_webhooks` to branch on `webhook_type`: discord → discord payload, generic → existing payload | AC-001, AC-011 | 20min | TASK-007, TASK-008 |
| TASK-010 | Load WebhookOptions for each webhook during dispatch (single query or lazy) | AC-005 | 15min | TASK-008 |
| TASK-011 | Handle Discord 429 rate limit — parse `Retry-After` header, wait, then retry | AC-010 | 30min | TASK-009 |

**Phase Duration**: ~2.5 hours

### Phase 3: API Endpoints

Update CRUD to handle new fields, add test message endpoint.

| Task ID | Description | ACs | Effort | Dependencies |
|---------|-------------|-----|--------|--------------|
| TASK-012 | Update `create_webhook` endpoint — create WebhookOptions row when `options` provided, validate Discord URL when type=discord | AC-005, AC-008 | 30min | Phase 1 |
| TASK-013 | Update `update_webhook` endpoint — update/create/delete WebhookOptions row | AC-005 | 20min | TASK-012 |
| TASK-014 | Update `list_webhooks` and response to include options and new fields | AC-005 | 15min | TASK-012 |
| TASK-015 | Add `POST /webhooks/{id}/test` endpoint — send test embed/payload | AC-009 | 30min | TASK-008 |
| TASK-016 | Update `delete_webhook` to cascade-delete WebhookOptions | AC-013 | 10min | TASK-012 |

**Phase Duration**: ~2 hours

### Phase 4: Verify & Polish

Run quality gates, ensure backward compatibility.

| Task ID | Description | ACs | Effort | Dependencies |
|---------|-------------|-----|--------|--------------|
| TASK-017 | Verify all existing webhook tests still pass (AC-011 backward compat) | AC-011 | 15min | Phase 2, 3 |
| TASK-018 | Lint + format pass (ruff) | — | 10min | TASK-017 |
| TASK-019 | Coverage check (target 80%+) | — | 10min | TASK-018 |

**Phase Duration**: ~30min

## Effort Summary

| Phase | Estimated Hours |
|-------|-----------------|
| Phase 1: Data Layer | 2.0 |
| Phase 2: Dispatcher Logic | 2.5 |
| Phase 3: API Endpoints | 2.0 |
| Phase 4: Verify & Polish | 0.5 |
| **Total** | **7.0** |

## Spec Traceability

| AC | Phase | Tasks | Test Coverage |
|----|-------|-------|---------------|
| AC-001 Discord embed format | Phase 2 | TASK-008, TASK-009 | Unit: discord payload builder; Integration: full dispatch |
| AC-002 Embed fields | Phase 2 | TASK-008 | Unit: payload field assertions |
| AC-003 Configurable color | Phase 2 | TASK-008 | Unit: color from options, default fallback |
| AC-004 Dashboard link in embed | Phase 2 | TASK-008 | Unit: link field present |
| AC-005 Discord options in WebhookOptions | Phase 1, 2, 3 | TASK-002, TASK-003, TASK-010, TASK-012 | Unit: CRUD with options; Unit: dispatch reads options |
| AC-006 Source filters | Phase 1, 2 | TASK-001, TASK-003, TASK-007 | Unit: filter match/skip logic |
| AC-007 Dispatcher skips filtered sources | Phase 2 | TASK-007 | Unit: source not in filter → skip |
| AC-008 Discord URL validation | Phase 1 | TASK-005 | Unit: valid/invalid URL rejection |
| AC-009 Test message endpoint | Phase 3 | TASK-015 | Unit: endpoint sends test payload |
| AC-010 Discord rate limit handling | Phase 2 | TASK-011 | Unit: 429 → wait Retry-After → retry |
| AC-011 Generic webhooks unchanged | Phase 2, 4 | TASK-009, TASK-017 | Existing tests pass unmodified |
| AC-012 webhook_type + source_filters columns | Phase 1 | TASK-001 | Unit: model fields exist, defaults correct |
| AC-013 WebhookOptions model | Phase 1 | TASK-002, TASK-006 | Unit: CRUD, FK relationship |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing webhook tests | Medium | High | Run existing test suite after each phase; AC-011 explicit backward compat |
| Discord API format changes | Low | Medium | Use documented embed format; structure is stable |
| Rate limit handling complexity | Low | Medium | Parse Retry-After header; cap max wait at 60s |
| WebhookOptions one-to-one enforcement | Low | Low | Unique constraint on webhook_endpoint_id |

## Dependencies

- Existing webhook service (specs/webhook-service.md) — already implemented and merged
- Discord webhook API docs (standard HTTP POST, no bot token)
- No new Python libraries required

## Deliverables

### Code
- `app/models/webhook.py` (modified — add webhook_type, source_filters)
- `app/models/webhook_options.py` (new)
- `app/schemas/webhook.py` (modified — add new fields)
- `app/services/webhook_dispatcher.py` (modified — source filtering, discord payload, rate limits)
- `app/api/endpoints/webhooks.py` (modified — options handling, test endpoint)

### Tests
- `tests/unit/test_discord_dispatcher.py` (new — discord payload, source filter, rate limit)
- `tests/unit/test_webhooks_api.py` (modified — new fields, discord URL validation, test endpoint)
- `tests/unit/test_discord_integration.py` (new — end-to-end discord flow)

## Next Steps

1. Review and approve this plan
2. Run `/add:tdd-cycle specs/discord-integration.md` to execute
3. Create PR for review and merge

## Plan History

- 2026-02-21: Initial plan created
