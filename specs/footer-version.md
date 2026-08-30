# Spec: version in the footer, click → changelog

## 1. Overview

The running version is currently visible only inside Settings → Changelog (and
the `/version` API). A conventional, always-visible home for it is the page
footer; clicking it should answer the natural follow-up — "what's in it?"

### User Story
As an operator, I want to see at a glance which version this instance runs
from any page, and clicking it should show me the changelog.

## 2. Acceptance Criteria

| ID | Criterion | Priority |
|----|-----------|----------|
| AC-001 | The server injects `window.__APP_VERSION__` into the SPA shell (alongside `__USER__`), so the footer needs no extra request and works before any query resolves. | Must |
| AC-002 | The SPA shell renders a footer on every page: muted "Rsync Viewer v{version}" where the version is a link to `/app/settings/changelog` (client-side navigation). A `dev` build shows "vdev" the same way. The footer must not collide with the fixed mobile bottom nav. | Must |
| AC-003 | The remaining server-rendered pages (login, register, password reset, notifications) get the same footer via `base.html` / the standalone auth templates, using the existing `app_version` template global; the link points at `/app/settings/changelog` (unauthenticated visitors pass through the login redirect and land there after signing in). | Must |
| AC-004 | Clicking the version in the SPA lands on the changelog section with the version list visible (existing section; no changes to it). | Must |

## 3. User Test Cases
- **TC-001** Open `/app` → footer shows "Rsync Viewer v2.20.0"; click the version → the changelog section renders with the "current" badge. (screenshot `tests/screenshots/footer-version/step-01-footer.png`)
- **TC-002** Open `/login` logged out → the same footer text is present.
- **TC-003** On a phone-width viewport the footer is readable above/behind the bottom nav without overlapping content.

## 4. Data / API
No new endpoints. Server → SPA handoff: `window.__APP_VERSION__: string`
(normalised, no `v` prefix — Settings already strips it). Jinja pages reuse the
`app_version` env global.

## 5. Edge Cases
- `__APP_VERSION__` missing/undefined (old cached shell): footer renders
  "Rsync Viewer" without a version link — never "vundefined".
- Version `dev`: shown as "vdev", still links to the changelog.

## 6. Screenshot Checkpoints
`tests/screenshots/footer-version/step-01-footer.png` (SPA, footer visible).
