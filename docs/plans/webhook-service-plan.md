# Implementation Plan: Webhook Notification Service

**Spec Version**: 0.1.0
**Created**: 2026-02-21
**Spec Reference**: specs/webhook-service.md

## Overview

Generic webhook dispatch service that sends HTTP POST notifications to configured URLs when FailureEvents are created. Includes retry with exponential backoff, auto-disable on repeated failures, CRUD API, and settings page UI.

## Implementation Phases

### Phase 1: Data Layer (Models + Schemas)

| Task | Description | AC Coverage | Files |
|------|-------------|-------------|-------|
| 1.1 | Create WebhookEndpoint model | AC-002 | app/models/webhook.py |
| 1.2 | Create NotificationLog model | AC-005 | app/models/notification_log.py |
| 1.3 | Create webhook CRUD schemas | AC-002, AC-008 | app/schemas/webhook.py |
| 1.4 | Create notification log read schema | AC-005 | app/schemas/notification_log.py |
| 1.5 | Register models in conftest.py and main.py for table creation | — | tests/conftest.py, app/main.py |

### Phase 2: API Endpoints

| Task | Description | AC Coverage | Files |
|------|-------------|-------------|-------|
| 2.1 | Create webhooks CRUD router (GET, POST, PUT, DELETE) | AC-002, AC-008, AC-011 | app/api/endpoints/webhooks.py |
| 2.2 | Register webhooks router in main.py | — | app/main.py |

### Phase 3: Webhook Dispatch Service

| Task | Description | AC Coverage | Files |
|------|-------------|-------------|-------|
| 3.1 | Create webhook dispatcher service with httpx | AC-001, AC-003, AC-010 | app/services/webhook_dispatcher.py |
| 3.2 | Implement retry with exponential backoff (30s, 60s, 120s) | AC-004 | app/services/webhook_dispatcher.py |
| 3.3 | Log each delivery attempt to NotificationLog | AC-005 | app/services/webhook_dispatcher.py |
| 3.4 | Auto-disable after 10 consecutive failures | AC-006 | app/services/webhook_dispatcher.py |
| 3.5 | Set FailureEvent.notified=True on success | AC-009 | app/services/webhook_dispatcher.py |
| 3.6 | Skip disabled webhooks | AC-011 | app/services/webhook_dispatcher.py |

### Phase 4: Integration

| Task | Description | AC Coverage | Files |
|------|-------------|-------------|-------|
| 4.1 | Call webhook dispatcher from sync_logs endpoint after FailureEvent creation | AC-001, AC-010 | app/api/endpoints/sync_logs.py |
| 4.2 | Call webhook dispatcher from stale_checker after stale FailureEvent creation | AC-001 | app/services/stale_checker.py |

### Phase 5: Settings UI

| Task | Description | AC Coverage | Files |
|------|-------------|-------------|-------|
| 5.1 | Add webhook management section to settings page | AC-007 | app/templates/settings.html |
| 5.2 | Create HTMX partials for webhook list and forms | AC-007 | app/templates/partials/webhook_*.html |
| 5.3 | Add HTMX endpoints for webhook management | AC-007 | app/main.py |

## Test Strategy

Tests will be organized by AC coverage:

| Test File | ACs Covered | Test Count (est.) |
|-----------|-------------|-------------------|
| tests/unit/test_webhooks_api.py | AC-002, AC-008, AC-011 | ~10 |
| tests/unit/test_webhook_dispatcher.py | AC-001, AC-003, AC-004, AC-005, AC-006, AC-009, AC-010 | ~12 |
| tests/unit/test_webhook_integration.py | AC-001 (end-to-end with sync_logs) | ~3 |

Key testing patterns:
- Mock httpx responses to simulate success/failure/timeout
- Use conftest fixtures for WebhookEndpoint creation
- Test retry behavior with mock delays (patch sleep/backoff)
- Test auto-disable threshold at exactly 10 consecutive failures

## Dependencies

- httpx already in requirements.txt (used for test client)
- No new dependencies needed — httpx supports async HTTP client natively

## Spec Traceability

| AC | Phase | Task | Test |
|----|-------|------|------|
| AC-001 | 3, 4 | 3.1, 4.1, 4.2 | test_ac001_* |
| AC-002 | 1, 2 | 1.1, 1.3, 2.1 | test_ac002_* |
| AC-003 | 3 | 3.1 | test_ac003_* |
| AC-004 | 3 | 3.2 | test_ac004_* |
| AC-005 | 1, 3 | 1.2, 1.4, 3.3 | test_ac005_* |
| AC-006 | 3 | 3.4 | test_ac006_* |
| AC-007 | 5 | 5.1, 5.2, 5.3 | (UI — manual verify) |
| AC-008 | 1, 2 | 1.3, 2.1 | test_ac008_* |
| AC-009 | 3 | 3.5 | test_ac009_* |
| AC-010 | 3, 4 | 3.1, 4.1 | test_ac010_* |
| AC-011 | 2, 3 | 2.1, 3.6 | test_ac011_* |
