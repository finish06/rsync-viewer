# Spec: synthetic check hygiene (fix)

## 1. Overview
Two long-standing defects in the synthetic monitor (user report 2026-08-30):
1. Every check leaks its `__synthetic_check` sync_log row: the cleanup step
   calls `DELETE /api/v1/sync-logs/{id}` with the API key, but that endpoint
   is JWT-admin-only, so it always fails (logged as "non-critical") — ~288
   leaked rows/day, ~50,000 on production.
2. On startup the check loop begins before the server accepts connections, so
   the first check fails with a connection error and dispatches a real
   failure webhook ("failed synthetic message") on every restart.

## 2. Acceptance Criteria
| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | After a successful POST-and-verify, the check removes its own sync_log row in-process (same DB session); no HTTP DELETE call remains. A check cycle leaves zero net rows. | Must |
| AC-002 | The background task waits for the app's own `/health` to respond (up to 60 s, polling) before the first check; during this warm-up no failure is recorded, no FailureEvent is created, and no webhook fires. After warm-up, failures count normally. | Must |
| AC-003 | Backlog purge: synthetic-source sync_logs older than one hour are deleted — once when monitoring starts and on every retention pass — regardless of the retention setting. Existing ~50k rows drain on the first start after deploy. | Must |
| AC-004 | Real sources are never touched by the purge; FailureEvents referencing purged synthetic logs are handled like retention does today. | Must |

## 3. User Test Cases
- **TC-001** Restart the app → no synthetic-failure webhook, pill reaches "UP" after the first interval. (verified on the local stack)
- **TC-002** After one check cycle, `SELECT count(*) FROM sync_logs WHERE source_name='__synthetic_check'` is unchanged from before the cycle.
