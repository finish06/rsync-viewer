# M11 — Polish & Infrastructure

**Goal:** UI consistency, email infrastructure, and codebase cleanup to prepare for OIDC (M7) and production hardening
**Status:** NEXT
**Appetite:** 1 week
**Target Maturity:** beta
**Started:** —
**Completed:** —

## Success Criteria

- [ ] SMTP email configuration manageable via admin Settings UI
- [ ] Test email can be sent from Settings to verify SMTP config
- [ ] SMTP credentials encrypted at rest (Fernet)
- [ ] Sync Logs filter box integrates quick-select date range buttons (matches Analytics pattern)
- [ ] Sync Logs page responsive down to phone with card layout below 768px
- [ ] Deprecated code and patterns cleaned up

## Hill Chart

```
SMTP Email Config      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Sync Logs UI Refresh   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Deprecation Cleanup    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Dev Seed Data          ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| SMTP Email Configuration | specs/smtp-email.md | SHAPED | Admin UI for SMTP setup, encrypted credentials, test email |
| Sync Logs UI Refresh | specs/sync-logs-ui-refresh.md | SHAPED | Integrated filter box, mobile card layout, responsive |
| Deprecation Cleanup | specs/deprecation-cleanup.md | SHAPED | Remove deprecated code, clean up patterns |
| Dev Seed Data | specs/dev-seed-data.md | SHAPED | Seed data tooling for development and testing |

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
