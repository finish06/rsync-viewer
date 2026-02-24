# M6 — Observability

**Goal:** Make the system observable for both machines (Prometheus metrics) and humans (comprehensive documentation)
**Status:** IN_PROGRESS
**Appetite:** 1 week
**Target Maturity:** beta
**Started:** 2026-02-23
**Completed:** —

## Success Criteria

- [ ] `/metrics` endpoint returns valid Prometheus exposition format
- [ ] Sync metrics exported: totals, duration histogram, files/bytes counters (per source)
- [ ] API metrics exported: request totals and duration histogram (per endpoint)
- [ ] Application health metrics: DB connections, app version
- [ ] Grafana dashboard JSON templates provided in `grafana/` directory
- [ ] Setup guide enables new developers to deploy using only documentation
- [ ] All environment variables documented with descriptions and defaults
- [ ] Architecture diagram and database schema documentation exist

## Hill Chart

```
Prometheus Metrics     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Grafana Dashboards     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Project Documentation  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Data Retention         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Prometheus Metrics Endpoint | specs/metrics-export.md | SHAPED | /metrics with sync, API, and health metrics |
| Grafana Dashboard Templates | specs/metrics-export.md | SHAPED | Sync overview + API performance dashboards |
| Data Retention Policies | specs/metrics-export.md | SHAPED | Configurable auto-cleanup of old sync logs |
| Setup & Deployment Guide | specs/documentation.md | SHAPED | Dev setup, Docker deployment, env var reference |
| Architecture Documentation | specs/documentation.md | SHAPED | System diagram, DB schema, data flow |
| Operational Documentation | specs/documentation.md | SHAPED | Troubleshooting guide, ingestion configuration |

## Dependencies

- M3 should be complete (documentation should reflect the hardened, stable codebase)
- M4 ideally complete (analytics endpoints and performance config should be documented)
- Metrics and documentation are independent of each other — can be worked in parallel

## Recommended Implementation Order

1. Prometheus Metrics Endpoint (standalone, no other feature depends on it)
2. Grafana Dashboard Templates (consumes metrics endpoint)
3. Data Retention (standalone background task)
4. Documentation (best written last — captures final state of all features)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Metrics overhead impacts request latency | Low | Low | prometheus-fastapi-instrumentator is lightweight |
| Documentation drifts from code | Medium | Medium | Add doc update reminder to PR template |
| Retention cascade delete breaks FK constraints | Low | High | Test cascade behavior, use soft delete if needed |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| cycle-5 | Prometheus Metrics, Data Retention | PLANNED | Metrics endpoint + retention background task |

## Retrospective

—
