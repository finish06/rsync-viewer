# M5 — API Performance

**Goal:** Reduce unnecessary database writes on hot paths by debouncing API key `last_used_at` updates
**Status:** PLANNED
**Appetite:** 2-3 days
**Target Maturity:** alpha
**Started:** —
**Completed:** —

## Success Criteria

- [ ] Authenticated API requests no longer commit `last_used_at` on every call
- [ ] Debounce interval configurable (default: 5 minutes)
- [ ] `last_used_at` still reflects recent usage (within debounce window)
- [ ] No regression in API key authentication behavior
- [ ] Zero additional latency on authenticated requests (faster, not slower)

## Problem

The current `verify_api_key` dependency (`app/api/deps.py:53-56`) writes `last_used_at` to the database and commits on every authenticated request:

```python
api_key.last_used_at = datetime.utcnow()
session.add(api_key)
session.commit()
```

For a homelab with moderate traffic this is tolerable, but it adds an unnecessary write + commit to every single API call. With monitoring endpoints polling frequently, this creates steady DB write pressure that provides minimal value — knowing the key was used "5 minutes ago" vs "right now" is equally useful.

## Hill Chart

```
API Key Debounce     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  SHAPED
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| API Key `last_used_at` Debounce | — | SHAPED | Time-based debounce to skip redundant writes |

## Approach Options

### Option A: Time-based check in `verify_api_key`
Compare `api_key.last_used_at` against current time. Only write if the difference exceeds the debounce interval. Simple, no new dependencies.

```python
if api_key.last_used_at is None or (
    datetime.utcnow() - api_key.last_used_at
).total_seconds() > DEBOUNCE_SECONDS:
    api_key.last_used_at = datetime.utcnow()
    session.add(api_key)
    session.commit()
```

### Option B: In-memory cache with periodic flush
Use a dict/TTL cache to track last update time per key. Flush to DB periodically. More complex but fully eliminates DB reads for the check.

**Recommended:** Option A — simplest, no new dependencies, immediately effective.

## Dependencies

- None — standalone optimization

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Stale `last_used_at` if app crashes before flush | Low | Low | Acceptable for homelab; within debounce window |
| Race condition with concurrent requests | Low | Low | Worst case: two writes within window, harmless |

## Cycles

| Cycle | Features | Status | Notes |
|-------|----------|--------|-------|
| cycle-1 | API Key Debounce | PLANNED | Spec → TDD cycle |

## Retrospective

—
