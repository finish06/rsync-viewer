# Implementation Plan: User Preferences

**Spec Version**: 0.1.0
**Created**: 2026-03-01
**Team Size**: Solo
**Estimated Duration**: 3–4 hours

## Overview

Persist user preferences (starting with theme) in a JSON column on the `users` table. Server injects theme into page `<head>` to avoid flash. JS saves preference changes via fire-and-forget PATCH to API. Unauthenticated users keep localStorage-only behavior.

## Objectives

- Add `preferences` JSON column to User model
- Create GET/PATCH `/api/v1/users/me/preferences` endpoints
- Inject theme server-side into templates for logged-in users
- Update theme.js to use server preference when available
- Maintain full backward compatibility for unauthenticated users

## Success Criteria

- [ ] All 12 acceptance criteria implemented and tested
- [ ] Code coverage >= 80%
- [ ] All quality gates passing (ruff, pytest)
- [ ] No flash of wrong theme for logged-in users
- [ ] Theme toggle still works instantly (fire-and-forget)

## Architecture Notes

**Database**: Project uses Alembic for migrations (2 existing in `alembic/versions/`). New migration adds `preferences JSONB DEFAULT '{}' NOT NULL` to `users` table. Existing rows get `{}` automatically.

**Template injection**: The inline `<script>` in `<head>` runs before CSS. Currently reads `localStorage.getItem('theme')`. For logged-in users, Jinja will render `window.__USER_THEME__ = "dark"` (or whatever) so JS picks it up before falling back to localStorage.

**Templates with inline theme script**: 5 files duplicate the same inline script block:
- `base.html` (all authenticated pages)
- `login.html`, `register.html`, `forgot_password.html`, `reset_password.html` (pre-auth pages — no user context, so no injection needed here)

**User context in templates**: Page routes pass `"user": user` explicitly in context. The `user` object comes from `OptionalUserDep`. Once we add `preferences` to the User model, it's automatically available in templates via `user.preferences`.

**API auth**: Preferences endpoints use `get_current_user` (requires authentication, any role).

## Implementation Phases

### Phase 1: Model + Schema (AC-001, AC-002, AC-011)

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-001 | Add `preferences` JSON column to User model (`app/models/user.py`). Type `Optional[dict]`, default `None`. SQLModel handles JSON serialization. | 10 min | — |
| TASK-002 | Create `UserPreferencesUpdate` Pydantic schema in `app/schemas/` with validation: `theme` must be one of `light`, `dark`, `system`. Unknown keys are stripped. | 15 min | — |
| TASK-003 | Create `UserPreferencesResponse` schema (returns full preferences dict) | 5 min | — |

**Files changed:**
- `app/models/user.py` — add `preferences` field
- `app/schemas/user.py` (or new `app/schemas/preferences.py`) — add schemas

### Phase 2: API Endpoints (AC-003, AC-004, AC-010, AC-011)

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-004 | Add `GET /api/v1/users/me/preferences` endpoint. Returns `user.preferences or {}`. Requires auth. | 15 min | TASK-001, TASK-003 |
| TASK-005 | Add `PATCH /api/v1/users/me/preferences` endpoint. Merges request body into existing preferences. Validates with schema. Returns updated preferences. | 20 min | TASK-001, TASK-002 |

**Files changed:**
- `app/api/endpoints/users.py` (or new file) — add endpoints
- `app/main.py` — register router if new file

### Phase 3: Server-Side Theme Injection (AC-005, AC-006)

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-006 | Modify `base.html` inline `<script>`: add `var serverTheme = '{{ user_theme }}';` before the localStorage read. JS uses `serverTheme \|\| localStorage.getItem('theme') \|\| 'system'`. | 15 min | TASK-001 |
| TASK-007 | Pass `user_theme` to template context. Two options: (a) add to each page route, or (b) add a Jinja2 template global via middleware. Option (b) is cleaner — add a `@app.middleware("http")` that reads user from JWT cookie and sets `request.state.user_theme`. Then use a template global function. | 30 min | TASK-001 |

**Key decision — TASK-007 approach:** Use a **template context processor** pattern. Add `user_theme` to `templates.env.globals` as a callable that reads from `request.state`. This avoids modifying every route. However, Jinja2Templates doesn't have native context processors. The simpler approach: since `user` is already passed in context by page routes, just read `user.preferences.theme` directly in the template. This requires no middleware — just a template change.

**Revised TASK-007:** No middleware needed. The `base.html` template already has access to `user` (passed in context). The inline script becomes:
```jinja
var serverTheme = {% if user and user.preferences %}'{{ user.preferences.get("theme", "") }}'{% else %}null{% endif %};
```

**Note:** The 4 pre-auth templates (`login.html`, `register.html`, `forgot_password.html`, `reset_password.html`) don't have `user` in context, so `serverTheme` will be `null` and they'll fall back to localStorage. This is correct behavior (AC-009).

**Files changed:**
- `app/templates/base.html` — modify inline script

### Phase 4: Client-Side JS Updates (AC-006, AC-007, AC-008, AC-009)

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-008 | Update `theme.js` `getPreference()`: check `window.__USER_THEME__` first (set by inline script), then localStorage. When server theme exists, also update localStorage to keep them in sync (AC-006). | 15 min | TASK-006 |
| TASK-009 | Update `theme.js` `setTheme()`: after saving to localStorage, fire background `PATCH /api/v1/users/me/preferences` with `{"theme": value}`. Use `fetch()` with `keepalive: true`. Catch and ignore errors (AC-008). Only fire if user is authenticated (check `window.__USER_THEME__ !== undefined` as proxy for "logged in"). | 20 min | TASK-005 |

**Files changed:**
- `app/static/js/theme.js` — modify `getPreference()` and `setTheme()`
- `app/templates/base.html` — set `window.__USER_THEME__` from Jinja context

### Phase 5: Tests (all ACs)

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-010 | Test: `preferences` column defaults and JSON handling (AC-001, AC-002) | 15 min | TASK-001 |
| TASK-011 | Test: `GET /api/v1/users/me/preferences` returns preferences, requires auth (AC-004, AC-010) | 15 min | TASK-004 |
| TASK-012 | Test: `PATCH /api/v1/users/me/preferences` merges, validates, rejects invalid values (AC-003, AC-011) | 20 min | TASK-005 |
| TASK-013 | Test: unauthenticated requests return 401 (AC-010) | 10 min | TASK-004, TASK-005 |
| TASK-014 | Test: empty PATCH body returns current preferences unchanged | 5 min | TASK-005 |
| TASK-015 | Test: unknown keys in PATCH body are ignored/stripped | 10 min | TASK-005 |

**Files changed:**
- `tests/test_user_preferences.py` — new test file

## Effort Summary

| Phase | Estimated | Tasks |
|-------|-----------|-------|
| Phase 1: Model + Schema | 30 min | 3 |
| Phase 2: API Endpoints | 35 min | 2 |
| Phase 3: Server-Side Injection | 30 min | 2 |
| Phase 4: Client-Side JS | 35 min | 2 |
| Phase 5: Tests | 75 min | 6 |
| **Total** | **~3.5 hours** | **15** |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| JSON column behavior differs between SQLite (tests) and Postgres (prod) | Medium | Medium | Use SQLModel's JSON type which handles both. Test with in-memory SQLite. |
| Inline script injection causes XSS if preference value is unsanitized | Low | High | Only allow enum values ("light", "dark", "system"). Validate on write AND use Jinja autoescaping. |
| Theme flash on first page load after login | Low | Low | The login redirect response won't have the theme injected. First dashboard load will have it. This is acceptable — one page load with localStorage fallback. |
| `user.preferences` is `None` for existing users | Medium | Low | All code uses `user.preferences or {}` / `.get("theme", "")` pattern. Template uses `{% if user and user.preferences %}`. |

## Spec Traceability

| Task | Acceptance Criteria |
|------|-------------------|
| TASK-001 | AC-001, AC-002 |
| TASK-002 | AC-002, AC-011 |
| TASK-003 | AC-004 |
| TASK-004 | AC-004, AC-010 |
| TASK-005 | AC-003, AC-010, AC-011 |
| TASK-006 | AC-005, AC-006 |
| TASK-007 | AC-005 |
| TASK-008 | AC-006, AC-009 |
| TASK-009 | AC-007, AC-008 |
| TASK-010 | AC-001, AC-002 |
| TASK-011 | AC-004, AC-010 |
| TASK-012 | AC-003, AC-011 |
| TASK-013 | AC-010 |
| TASK-014 | AC-003 |
| TASK-015 | AC-011 |

## Deliverables

| File | Action |
|------|--------|
| `app/models/user.py` | Edit — add `preferences` JSON column |
| `app/schemas/preferences.py` | Create — validation schemas |
| `app/api/endpoints/preferences.py` | Create — GET/PATCH endpoints |
| `app/main.py` | Edit — register preferences router |
| `app/templates/base.html` | Edit — inject `window.__USER_THEME__` |
| `app/static/js/theme.js` | Edit — read server theme, fire-and-forget PATCH |
| `tests/test_user_preferences.py` | Create — full test coverage |

## Migration Note

Alembic migration required (AC-012). The project uses Alembic (`alembic/versions/` has 2 existing migrations, `entrypoint.sh` runs `alembic upgrade head` on startup). Generate via `alembic revision --autogenerate -m "add preferences to users"`. Column: `JSONB`, server_default=`'{}'`, nullable=False. Production DB gets the column automatically on next deploy.

## Next Steps

1. Approve this plan
2. Execute phases 1–5 sequentially
3. Run quality gates (`ruff`, `pytest`)
4. Open PR

## Plan History

- 2026-03-01: Initial plan created
