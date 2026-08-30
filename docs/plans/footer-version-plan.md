# Plan: footer version → changelog

**Spec:** specs/footer-version.md · **Branch:** `feature/footer-version` · **Release:** v2.21.0 (`feat:` → minor)

## Tasks
| # | Task | Files | AC |
|---|------|-------|----|
| T1 | Inject `window.__APP_VERSION__` in the SPA shell script | `app/routes/spa.py` | AC-001 |
| T2 | `appVersion()` accessor + `Window` typing; footer in the Shell (link → `/app/settings/changelog`, mobile-safe spacing) | `frontend/src/app/user.ts` (typing) or new `version.ts`, `frontend/src/app/Shell.tsx` | AC-002, AC-004 |
| T3 | Footer on server-rendered pages: `base.html` + the four standalone auth templates (shared include) | `app/templates/base.html`, `login/register/forgot_password/reset_password.html` | AC-003 |
| T4 | Tests: spa-serving injection test; Shell footer test (version link, missing-version fallback); template footer test; E2E TC-001 + screenshot | `tests/test_spa_serving.py`, `frontend/src/app/Shell.test.tsx`, `tests/test_jwt_auth.py` or new, `tests/e2e/` | all |

## Test strategy
RED first: backend asserts `__APP_VERSION__` in the served shell; Shell test asserts footer text + href and the no-version fallback; a route test asserts the footer on `/login`; E2E clicks the version and expects the changelog section.

## Risks
- Old cached `index.html` without the injection → fallback renders no version (AC edge case) — guard in the accessor.
