"""Serve the built React SPA (specs/insight-ui.md AC-022).

The Vite build lands in ``settings.spa_dist_dir`` (default ``app/static/app``);
hashed assets are served by the ``/static`` mount, and every ``/app`` route
returns ``index.html`` so client-side routing survives deep links and reloads.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.config import Settings, get_settings

router = APIRouter()

SPA_MISSING_DETAIL = (
    "Frontend build not found. Run `npm run build` in frontend/ "
    "(or build the Docker image) to generate app/static/app/index.html."
)


def _index_response(settings: Settings) -> FileResponse:
    index = Path(settings.spa_dist_dir) / "index.html"
    if not index.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=SPA_MISSING_DETAIL
        )
    return FileResponse(index, headers={"Cache-Control": "no-store"})


@router.get("/app", include_in_schema=False)
@router.get("/app/{path:path}", include_in_schema=False)
async def spa_index(settings: Settings = Depends(get_settings)) -> FileResponse:
    """Return the SPA shell for any /app route; the client router takes over."""
    return _index_response(settings)
