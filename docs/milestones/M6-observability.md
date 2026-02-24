# M6 — Observability

**Goal:** Make the system observable for both machines (Prometheus metrics) and humans (comprehensive documentation)
**Status:** COMPLETE
**Appetite:** 1 week
**Target Maturity:** beta
**Started:** 2026-02-23
**Completed:** 2026-02-24

## Success Criteria

- [x] `/metrics` endpoint returns valid Prometheus exposition format
- [x] Sync metrics exported: totals, duration histogram, files/bytes counters (per source)
- [x] API metrics exported: request totals and duration histogram (per endpoint)
- [x] Application health metrics: DB connections, app version
- [x] Grafana dashboard JSON templates provided in `grafana/` directory
- [x] Setup guide enables new developers to deploy using only documentation
- [x] All environment variables documented with descriptions and defaults
- [x] Architecture diagram and database schema documentation exist

## Hill Chart

```
Prometheus Metrics     ████████████████████████████████████  DONE
Data Retention         ████████████████████████████████████  DONE
Grafana Dashboards     ████████████████████████████████████  DONE
Project Documentation  ████████████████████████████████████  DONE
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Prometheus Metrics Endpoint | specs/metrics-export.md | DONE | /metrics with sync, API, and health metrics (v1.6.0) |
| Data Retention Policies | specs/metrics-export.md | DONE | Configurable auto-cleanup with FK cascade (v1.6.0) |
| Grafana Dashboard Templates | specs/metrics-export.md | DONE | Sync overview + API performance dashboards |
| Setup & Deployment Guide | specs/documentation.md | DONE | Dev setup, Docker deployment, env var reference |
| Architecture Documentation | specs/documentation.md | DONE | System diagram, DB schema, data flow |
| Operational Documentation | specs/documentation.md | DONE | Troubleshooting guide, ingestion configuration |

## Dependencies

- M3 should be complete (documentation should reflect the hardened, stable codebase)
- M4 ideally complete (analytics endpoints and performance config should be documented)
- Metrics and documentation are independent of each other — can be worked in parallel

## Recommended Implementation Order

1. ~~Prometheus Metrics Endpoint~~ (DONE — v1.6.0)
2. ~~Data Retention~~ (DONE — v1.6.0)
3. Project Documentation (cycle-6)
4. Grafana Dashboard Templates (cycle-6)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| ~~Metrics overhead impacts request latency~~ | ~~Low~~ | ~~Low~~ | Verified < 5ms overhead |
| Documentation drifts from code | Medium | Medium | Add doc update reminder to PR template |
| ~~Retention cascade delete breaks FK constraints~~ | ~~Low~~ | ~~High~~ | Tested and verified cascade behavior |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| cycle-5 | Prometheus Metrics, Data Retention | COMPLETE | 26 tests, merged PR #10, tagged v1.6.0 |
| cycle-6 | Project Documentation, Grafana Dashboards | COMPLETE | 27 tests, 6 doc files + 2 Grafana dashboards |

## Retrospective

**Completed:** 2026-02-24 (2 cycles over 2 days)

**What went well:**
- TDD for documentation worked cleanly — 27 tests written first, then docs to satisfy them
- Grafana dashboards were straightforward once metric names were established in cycle-5
- Prometheus metrics + data retention (cycle-5) and docs + Grafana (cycle-6) parallelized naturally

**What was harder than expected:**
- Playwright e2e test isolation: sync_api event loop contaminated pytest-asyncio, required custom `pytest_collection_modifyitems` hook to skip e2e by default
- CI test container needed explicit volume mounts for `docs/` and `grafana/` directories

**Metrics:**
- 2 cycles, 53 new tests (26 metrics + 27 docs)
- 6 documentation files, 2 Grafana dashboard templates
- 403 total tests passing, 93% coverage maintained
