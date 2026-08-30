# Spec: CI/CD — single-run testing, official releases, update awareness

## 1. Overview

Three problems with the current pipeline:
1. Every test suite runs three times per change — locally in the pre-commit
   hook, in PR CI, and again on the merge push to `main`. Only the PR run
   gates anything.
2. Merges auto-tag `vX.Y.Z` but a GitHub Release only exists when someone
   creates it by hand — versions are not *officially* released.
3. A self-hosted install has no way to know a newer version exists.

### User Story
As a homelab operator running Rsync Viewer, I want every merged version to be
an official GitHub Release and my running instance to tell me when an update
is available, and as the maintainer I want each test suite to run exactly
once, at the stage where it gates something.

## 2. Acceptance Criteria

### Test stages (run once, at the right time)
| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | Lint, type-check, backend tests+coverage, frontend suite and security audit run on `pull_request` events only. A push to `main` runs no unit/integration suite — it runs tag → container build → smoke tests → release. Branch protection keeps the PR jobs required. | Must |
| AC-002 | The local pre-commit hook runs static checks only (ruff format, ruff check, mypy — seconds); the full pytest run happens in PR CI. The hook script is committed under `scripts/git-hooks/` with install instructions so the behaviour is official, not machine-local. | Must |
| AC-003 | Post-merge verification is the smoke suite against the freshly built container (unchanged); the weekly scheduled dependency audit remains. | Must |

### Official releases
| ID | Criterion | Priority |
|----|-----------|----------|
| AC-004 | After the auto-tag lands on `main`, CI publishes a GitHub Release for that tag, marked latest, with notes taken from the matching `CHANGELOG.md` section (fallback: auto-generated notes). Re-runs are idempotent — an existing release is left alone. | Must |
| AC-005 | The release is created only after the container build for that version succeeds (a release always has a pullable image). | Must |

### Update awareness in the UI
| ID | Criterion | Priority |
|----|-----------|----------|
| AC-006 | `GET /api/v1/version/updates` (viewer auth) returns `{current, latest, update_available, release_url, published_at, checked_at}`. `latest` comes from the GitHub Releases API, cached in-process for `UPDATE_CHECK_TTL_SECONDS` (default 21600). Failures and `current="dev"` degrade to `update_available: false, latest: null` — never an error. `UPDATE_CHECK_ENABLED=false` disables the outbound call entirely. | Must |
| AC-007 | Comparison is semantic (`2.9.0 < 2.10.0`), tolerant of a leading `v`. | Must |
| AC-008 | When an update is available the SPA shows a badge dot on the Settings-menu button and an "Update available — vX.Y.Z" menu item linking to the release; the Changelog settings section shows the same notice above the version list. No update → no badge, no item, no notice. | Must |

## 3. User Test Cases
- **TC-001** Merge a `feat:` PR → main pipeline tags `vX.(Y+1).0`, pushes the image, smoke passes, and a GitHub Release with the CHANGELOG section appears — no human step.
- **TC-002** Open the SPA on an instance running an older version → gear badge dot visible; the menu names the newer version and links to its release page; Changelog section shows the notice.
- **TC-003** Run the instance with no network access to GitHub → no badge, no errors in the console or logs beyond one debug line.
- **TC-004** Push a PR → suites run once; merge it → only build/smoke/release jobs run (checks list on the merge commit shows no duplicate suite runs).

## 4. API Contract
`GET /api/v1/version/updates` → 200
```json
{
  "current": "2.17.0",
  "latest": "2.18.0",
  "update_available": true,
  "release_url": "https://github.com/finish06/rsync-viewer/releases/tag/v2.18.0",
  "published_at": "2026-08-30T12:00:00Z",
  "checked_at": "2026-08-30T18:00:00Z"
}
```

## 5. Edge Cases
- GitHub rate-limit / timeout → serve stale cache if present, else `latest: null`.
- Prerelease/draft releases are ignored (`releases/latest` already excludes them).
- `current` newer than `latest` (local build ahead) → `update_available: false`.
- Two PRs merged in quick succession: each push tags and releases its own version; concurrency group serialises the pipeline per ref.

## 6. Screenshot Checkpoints
- `tests/screenshots/cicd-release/step-01-update-badge.png` — gear badge + menu item (E2E optional; Vitest asserts the DOM).
