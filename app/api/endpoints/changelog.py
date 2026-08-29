"""Changelog API (specs/settings-ui.md AC-009). Any authenticated user."""

from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import require_role_or_api_key
from app.config import get_settings
from app.schemas.changelog import ChangelogVersion
from app.services.auth import ROLE_VIEWER
from app.services.changelog_parser import parse_changelog

router = APIRouter(
    prefix="/changelog",
    tags=["changelog"],
    dependencies=[Depends(require_role_or_api_key(ROLE_VIEWER))],
)

DEFAULT_VERSIONS = 5


class ChangelogResponse(BaseModel):
    app_version: str
    versions: list[ChangelogVersion]
    has_more: bool


@router.get("", response_model=ChangelogResponse)
async def read_changelog(
    all: bool = Query(False, description="Return every released version"),
) -> ChangelogResponse:
    """Released versions from CHANGELOG.md, newest first (Unreleased omitted)."""
    versions = [
        v
        for v in parse_changelog(path=Path("CHANGELOG.md"))
        if v.version != "Unreleased"
    ]
    has_more = len(versions) > DEFAULT_VERSIONS and not all
    return ChangelogResponse(
        app_version=get_settings().app_version,
        versions=versions if all else versions[:DEFAULT_VERSIONS],
        has_more=has_more,
    )
