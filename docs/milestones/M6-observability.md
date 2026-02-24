# M6 — Observability

**Goal:** Make the system observable for both machines (Prometheus metrics) and humans (comprehensive documentation)
**Status:** IN_PROGRESS
**Appetite:** 1 week
**Target Maturity:** beta
**Started:** 2026-02-23
**Completed:** —

## Success Criteria

- [x] `/metrics` endpoint returns valid Prometheus exposition format
- [x] Sync metrics exported: totals, duration histogram, files/bytes counters (per source)
- [x] API metrics exported: request totals and duration histogram (per endpoint)
- [x] Application health metrics: DB connections, app version
- [ ] Grafana dashboard JSON templates provided in `grafana/` directory
- [ ] Setup guide enables new developers to deploy using only documentation
- [ ] All environment variables documented with descriptions and defaults
- [ ] Architecture diagram and database schema documentation exist

## Hill Chart

```
Prometheus Metrics     ████████████████████████████████████  DONE
Data Retention         ████████████████████████████████████  DONE
Grafana Dashboards     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Project Documentation  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Prometheus Metrics Endpoint | specs/metrics-export.md | DONE | /metrics with sync, API, and health metrics (v1.6.0) |
| Data Retention Policies | specs/metrics-export.md | DONE | Configurable auto-cleanup with FK cascade (v1.6.0) |
| Grafana Dashboard Templates | specs/metrics-export.md | SHAPED | Sync overview + API performance dashboards |
| Setup & Deployment Guide | specs/documentation.md | SHAPED | Dev setup, Docker deployment, env var reference |
| Architecture Documentation | specs/documentation.md | SHAPED | System diagram, DB schema, data flow |
| Operational Documentation | specs/documentation.md | SHAPED | Troubleshooting guide, ingestion configuration |

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
| cycle-6 | Project Documentation, Grafana Dashboards | PLANNED | Docs first, then Grafana |

## Retrospective

—
