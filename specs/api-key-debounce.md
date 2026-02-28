# Spec: API Key `last_used_at` Debounce

**Version:** 0.1.0
**Created:** 2026-02-22
**PRD Reference:** docs/prd.md — M5: API Performance
**Status:** Complete
**Milestone:** M5 — API Performance

## 1. Overview

Reduce unnecessary database writes by debouncing the `last_used_at` timestamp update on API key authentication. Instead of writing to the database on every authenticated request, only write when the existing timestamp is stale (older than the debounce interval).

### User Story

As a homelab admin, I want the API key authentication to be efficient, so that frequent API calls (e.g., monitoring endpoints) don't create unnecessary database write pressure.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | When `last_used_at` is NULL (first use), the timestamp is written immediately | Must |
| AC-002 | When `last_used_at` is older than 5 minutes, the timestamp is updated | Must |
| AC-003 | When `last_used_at` is within the last 5 minutes, no database write occurs | Must |
| AC-004 | The debounce does not affect API key validation (valid/invalid/missing checks still work) | Must |
| AC-005 | The debounce interval is configurable via settings (default: 5 minutes) | Should |

## 3. User Test Cases

### TC-001: First API Key Usage

**Precondition:** API key exists with `last_used_at = NULL`.
**Steps:**
1. Make an authenticated API request
**Expected:** `last_used_at` is set to current time.

### TC-002: Rapid Successive Requests

**Precondition:** API key was used 1 minute ago.
**Steps:**
1. Make an authenticated API request
**Expected:** `last_used_at` is NOT updated (still shows the time from 1 minute ago).

### TC-003: Stale Key Usage

**Precondition:** API key was used 10 minutes ago.
**Steps:**
1. Make an authenticated API request
**Expected:** `last_used_at` is updated to current time.

## 4. Data Model

Already exists — no new models needed.

### ApiKey (existing)
| Field | Type | Notes |
|-------|------|-------|
| last_used_at | datetime? | Nullable, updated with debounce |

## 5. Implementation Location

- `app/api/deps.py` — `verify_api_key` function (already implemented)

## 6. Edge Cases

- Concurrent requests within the debounce window — at most one extra write, acceptable
- App crash before flush — last_used_at is stale by at most debounce interval, acceptable
- Clock skew — not applicable for single-server homelab deployment
