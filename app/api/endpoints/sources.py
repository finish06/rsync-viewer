"""Source health API (specs/insight-ui.md AC-005)."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, require_role_or_api_key
from app.schemas.source_health import SourceHealth
from app.services.auth import ROLE_VIEWER
from app.services.source_health import get_source_health

router = APIRouter(
    prefix="/sources",
    tags=["sources"],
    dependencies=[Depends(require_role_or_api_key(ROLE_VIEWER))],
)


@router.get(
    "/health",
    response_model=list[SourceHealth],
    summary="Per-source liveness, failure streak, and daily activity",
)
async def sources_health(
    session: SessionDep,
    days: int = Query(14, ge=1, le=90, description="Length of the daily series"),
) -> list[SourceHealth]:
    """One entry per source that has synced or has a monitor."""
    return get_source_health(session, days=days)
