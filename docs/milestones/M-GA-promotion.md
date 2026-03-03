# M-GA: Maturity Promotion — Beta to GA

**Goal:** Promote rsync-viewer from Beta to General Availability (v2.0.0)
**Promoted:** 2026-03-03
**Appetite:** 1 day
**Version:** 2.0.0

## Gap Analysis Summary

Assessment performed against GA maturity checklist from `maturity-lifecycle.md`:

| Requirement | Status | Notes |
|-------------|--------|-------|
| All milestones complete | PASS | M1-M11 complete |
| 80%+ test coverage sustained | PASS | 83% at last CI run |
| SLAs defined | PASS | Added to config.json and PRD |
| Smoke tests | PASS | 7 tests in tests/smoke/ |
| PR template | PASS | .github/PULL_REQUEST_TEMPLATE.md |
| Project glossary | PASS | docs/glossary.md (15 terms) |
| Docker tag strategy | PASS | latest + sha + version tags |
| Protected branches | PASS | main branch protected |
| CI pipeline | PASS | lint + typecheck + test + build + smoke |

## Homelab Calibration

Several GA requirements were calibrated for a solo homelab project:

- **Two-reviewer policy:** N/A — solo project, single reviewer
- **Module READMEs:** Deferred — low value for solo maintainer
- **File length refactoring:** Tracked but not blocking — 7 files over 300 lines
- **N+1 query detection in CI:** Deferred — advisory, not blocking
- **Performance regression suite:** Deferred — Prometheus metrics serve this role
- **30+ days stability:** 12 days since beta (2026-02-24). Accepted based on zero production incidents and all milestones verified.
- **SLAs:** Defined as monitoring thresholds, not contractual commitments

## What Was Completed

1. **Smoke test suite** — 7 standalone tests against live instance
2. **PR template** — Standard quality checklist for all PRs
3. **Project glossary** — 15 domain terms for onboarding clarity
4. **SLA targets** — Availability, latency, and ingestion thresholds
5. **Docker tag strategy** — Production-grade tagging (latest, sha, version)
6. **CI smoke job** — Smoke tests run after every main branch build
7. **Version bump** — 1.11.0 → 2.0.0
8. **Maturity config** — beta → ga in .add/config.json

## Promotion Rationale

- All 11 milestones complete (M1-M11)
- 650+ tests, 83% coverage
- Full feature set: multi-user auth, OIDC SSO, webhook notifications, Prometheus metrics, data retention, rsync client containers
- CI pipeline with lint, type check, tests, coverage, container build
- Zero production incidents since beta promotion
- Comprehensive documentation: architecture, setup, environment vars, troubleshooting, ingestion guide

## Hill Chart

```
SHAPED ─── SPECCED ─── PLANNED ─── IN_PROGRESS ─── VERIFIED ─── DONE
                                                                  ▲
                                                          All features
```

## Success Criteria

- [x] Smoke tests written and passing
- [x] PR template created
- [x] Glossary published
- [x] SLAs defined in config and PRD
- [x] Docker tags updated for GA
- [x] Version bumped to 2.0.0
- [x] Maturity set to ga
- [x] CHANGELOG updated
