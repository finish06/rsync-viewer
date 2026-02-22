# M5 — API Performance

**Goal:** Reduce unnecessary database writes on hot paths by debouncing API key `last_used_at` updates
**Status:** COMPLETE
**Appetite:** 2-3 days
**Target Maturity:** alpha
**Started:** 2026-02-21
**Completed:** 2026-02-21

## Success Criteria

- [x] Authenticated API requests no longer commit `last_used_at` on every call
- [x] Debounce interval configurable (default: 5 minutes)
- [x] `last_used_at` still reflects recent usage (within debounce window)
- [x] No regression in API key authentication behavior
- [x] Zero additional latency on authenticated requests (faster, not slower)

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
API Key Debounce     ████████████████████████████████████  DONE
```

## Features

| Feature | Spec | Position | Notes |
|---------|------|----------|-------|
| API Key `last_used_at` Debounce | specs/api-key-debounce.md | DONE | Time-based debounce, 10 tests, all passing |

## Approach

**Option A (implemented):** Time-based check in `verify_api_key` — compare `api_key.last_used_at` against current time, only write if the difference exceeds 5 minutes. Simple, no new dependencies.

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
| cycle-1 | API Key Debounce | COMPLETE | Implementation pre-existed, added spec + 10 tests |

## Retrospective

—
