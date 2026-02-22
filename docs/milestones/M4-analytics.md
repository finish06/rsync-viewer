# M4 — Analytics & Integrations

**Goal:** Enhanced visualizations, per-source dashboards, trend analysis, and Home Assistant webhook integration
**Status:** PLANNED
**Appetite:** 2 weeks
**Target Maturity:** beta
**Started:** —
**Completed:** —

## Success Criteria

- [ ] Per-source dashboard pages with dedicated stats and charts
- [ ] Trend analysis — sync duration, file count, bytes transferred over time
- [ ] Home Assistant webhook integration tested and working
- [ ] HA webhook format compatible with HA automation triggers
- [ ] Comparison views across sources (side-by-side or overlay charts)

## Hill Chart

```
Per-Source Dashboards  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Trend Analysis         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
Home Assistant         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| Per-Source Dashboards | — | SHAPED | Dedicated page per source with stats, recent syncs, charts |
| Trend Analysis | — | SHAPED | Time-series charts for duration, file count, bytes |
| Home Assistant Integration | — | SHAPED | HA webhook format, automation-compatible payloads (moved from M2) |

## Dependencies

- M2 must be complete (webhook backend + Discord integration provide the foundation for HA)
- Existing sync log data provides the basis for analytics charts
- Chart.js or similar already in use for basic charts — extend for trend analysis

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| HA webhook format changes between versions | Low | Medium | Test against current HA version, document format |
| Chart performance with large datasets | Medium | Medium | Pagination, date range limits, server-side aggregation |
| Per-source pages need design decisions | Medium | Low | Follow existing dashboard patterns, keep simple |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| — | — | — | Cycles to be planned when milestone starts |

## Retrospective

—
