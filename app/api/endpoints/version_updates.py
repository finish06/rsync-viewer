"""Update-availability API for the SPA (specs/cicd-release.md AC-006)."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_role_or_api_key
from app.config import get_settings
from app.services.auth import ROLE_VIEWER
from app.services.update_check import get_update_status

router = APIRouter(
    prefix="/version",
    tags=["version"],
    dependencies=[Depends(require_role_or_api_key(ROLE_VIEWER))],
)


class UpdateStatusRead(BaseModel):
    current: str
    latest: Optional[str]
    update_available: bool
    release_url: Optional[str]
    published_at: Optional[str]
    checked_at: Optional[datetime]


@router.get(
    "/updates",
    response_model=UpdateStatusRead,
    summary="Is a newer release available?",
)
async def read_update_status() -> UpdateStatusRead:
    """Compare the running version with the latest GitHub Release (cached)."""
    status = await get_update_status(current=get_settings().app_version)
    return UpdateStatusRead(**status.__dict__)
