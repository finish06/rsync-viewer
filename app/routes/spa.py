"""Serve the built React SPA (specs/insight-ui.md AC-022, AC-024).

The Vite build lands in ``settings.spa_dist_dir`` (default ``app/static/app``);
hashed assets are served by the ``/static`` mount, and ``/`` plus every
``/app`` route return ``index.html`` so client-side routing survives deep
links and reloads. The signed-in user's identity and theme preference are
injected at the top of ``<head>`` so the shell can apply the theme before
first paint and render a role-aware menu without a round trip.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.api.deps import OptionalUserDep
from app.config import Settings, get_settings

router = APIRouter()

SPA_MISSING_DETAIL = (
    "Frontend build not found. Run `npm run build` in frontend/ "
    "(or build the Docker image) to generate app/static/app/index.html."
)

# Legacy dashboard deep links (``/?tab=…``) map onto SPA / server pages.
LEGACY_TAB_TARGETS = {"analytics": "/app/trends", "notifications": "/notifications"}


def _user_context_script(user) -> str:
    """Inline script with the current user; JSON is made safe for a <script> body."""
    theme = (user.preferences or {}).get("theme") if user else None
    payload = {
        "username": user.username if user else None,
        "role": user.role if user else None,
        "theme": theme,
    }
    safe = json.dumps(payload).replace("</", "<\\/")
    theme_js = json.dumps(theme).replace("</", "<\\/") if theme else "null"
    return (
        f"<script>window.__USER__ = {safe};window.__USER_THEME__ = {theme_js};</script>"
    )


def _index_response(settings: Settings, user=None) -> Response:
    index = Path(settings.spa_dist_dir) / "index.html"
    if not index.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=SPA_MISSING_DETAIL
        )
    html = index.read_text(encoding="utf-8")
    html = html.replace("<head>", "<head>" + _user_context_script(user), 1)
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@router.get("/", include_in_schema=False)
async def root(
    user: OptionalUserDep = None,
    tab: Optional[str] = Query(None),
    settings: Settings = Depends(get_settings),
) -> Response:
    """The dashboard is the SPA; legacy ``?tab=`` links redirect to their new home."""
    if tab in LEGACY_TAB_TARGETS:
        return RedirectResponse(url=LEGACY_TAB_TARGETS[tab], status_code=302)
    return _index_response(settings, user)


@router.get("/app", include_in_schema=False)
@router.get("/app/{path:path}", include_in_schema=False)
async def spa_index(
    user: OptionalUserDep = None, settings: Settings = Depends(get_settings)
) -> Response:
    """Return the SPA shell for any /app route; the client router takes over."""
    return _index_response(settings, user)
