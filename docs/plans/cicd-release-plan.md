# Plan: CI/CD single-run testing, official releases, update awareness

**Spec:** specs/cicd-release.md · **Branch:** `feature/cicd-release` · **Release:** v2.18.0 (`feat:` → minor)

## Tasks
| # | Task | Files | AC |
|---|------|-------|----|
| T1 | Split workflows: `ci.yml` → `pull_request` + weekly schedule only; new `release.yml` on push to `main`/`beta`: version job (moved auto-tag logic) → build-push → smoke → `release` job (`gh release create` from CHANGELOG section, idempotent) | `.github/workflows/ci.yml`, `.github/workflows/release.yml` | AC-001, AC-003, AC-004, AC-005 |
| T2 | Pre-commit hook → static checks (ruff format/check + mypy); committed copy + installer note | `scripts/git-hooks/pre-commit`, `.git/hooks/pre-commit` (local), README | AC-002 |
| T3 | Update-check service: cached GitHub `releases/latest` lookup, semver compare; settings `update_check_enabled`, `update_check_ttl_seconds` | `app/services/update_check.py`, `app/config.py` | AC-006, AC-007 |
| T4 | `GET /api/v1/version/updates` endpoint + schema | `app/api/endpoints/version_updates.py` (or extend existing), `app/schemas/` | AC-006 |
| T5 | SPA: `useUpdateCheck` hook, gear badge + menu item, Changelog notice | `frontend/src/api/{types,hooks}.ts`, `app/Shell.tsx`, `features/settings/ChangelogSection.tsx`, MSW handlers | AC-008 |
| T6 | CHANGELOG 2.18.0; verify workflows parse (`python -c yaml`), local QA | `CHANGELOG.md` | — |

## Test strategy (RED first)
- Backend `tests/test_update_check.py`: semver compare table; cache TTL honoured (patched clock/httpx); failure → `latest None`; disabled → no outbound call; endpoint shape + viewer auth.
- Frontend: Shell badge shown/hidden per MSW response; menu item links release_url; ChangelogSection notice.
- Workflows: YAML validity check in-repo; TC-004 verified live on the next real PR/merge (this one).

## Risks
- Merge commit differs from tested PR head (semantic conflicts between racing PRs) — accepted per goal; smoke tests remain the post-merge net; solo-maintainer flow makes races rare.
- GitHub API unauthenticated limit (60/h/IP) — 6 h TTL keeps a single instance at ≤4 calls/day.
- `needs:` chains with skipped jobs silently skip dependents — avoided by moving push-time jobs into their own workflow instead of `if:`-guarding shared jobs.
