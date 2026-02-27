# M11 — Polish & Infrastructure

**Goal:** UI consistency, email infrastructure, and codebase cleanup to prepare for OIDC (M7) and production hardening
**Status:** IN_PROGRESS
**Appetite:** 1 week
**Target Maturity:** beta
**Started:** 2026-02-26
**Completed:** —

## Success Criteria

- [x] SMTP email configuration manageable via admin Settings UI
- [x] Test email can be sent from Settings to verify SMTP config
- [x] SMTP credentials encrypted at rest (Fernet)
- [x] Sync Logs filter box integrates quick-select date range buttons (matches Analytics pattern)
- [x] Sync Logs page responsive down to phone with card layout below 768px
- [x] Deprecated code and patterns cleaned up

## Hill Chart

```
SMTP Email Config      ████████████████████████████████░░░░  VERIFIED
Sync Logs UI Refresh   ████████████████████████████████░░░░  VERIFIED
Deprecation Cleanup    ████████████████████████████████████  DONE
Dev Seed Data          ████████████████████████████████████  DONE
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| SMTP Email Configuration | specs/smtp-email.md | VERIFIED | Model, service, admin UI, Fernet encryption, test email — 2ee116a |
| Sync Logs UI Refresh | specs/sync-logs-ui-refresh.md | VERIFIED | Quick-select in filter box, mobile cards, responsive layout — ea7784f |
| Deprecation Cleanup | specs/deprecation-cleanup.md | DONE | All datetime.utcnow() replaced with utc_now() helper |
| Dev Seed Data | specs/dev-seed-data.md | DONE | Seed data with users, API key, sync logs, webhooks, notifications — d51fd89 |

## Dependencies

- M9 must be complete (Admin role required for SMTP settings, User model for email addresses)
- SMTP email is a prerequisite for M7 OIDC (password reset emails)
- No dependencies between the 3 features — can be parallelized

## Recommended Implementation Order

1. Deprecation Cleanup (cleans codebase before new features)
2. Sync Logs UI Refresh (standalone UI work, no backend changes)
3. SMTP Email Configuration (new model + service + UI, sets up email infra for M7)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SMTP config encryption key management | Low | High | Share ENCRYPTION_KEY with future OIDC config, document rotation |
| Mobile card layout complexity | Low | Medium | Progressive enhancement — table works as fallback |
| Deprecation cleanup breaks existing behavior | Low | Medium | Full test suite must pass after cleanup |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| — | — | — | — |

## Retrospective

—
