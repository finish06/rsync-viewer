"""Update awareness — is a newer GitHub Release available? (cicd-release AC-006/007).

The lookup is cached in-process and degrades to "no update" on any failure:
a homelab box with no outbound network must never see errors from this.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from app.config import get_settings
from app.utils import utc_now

logger = logging.getLogger(__name__)

RELEASES_URL = "https://api.github.com/repos/finish06/rsync-viewer/releases/latest"
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

# Module-level cache: {"release": dict | None, "checked_at": datetime}
_cache: dict[str, Any] = {}


def clear_cache() -> None:
    _cache.clear()


def _parse(version: str) -> Optional[tuple[int, int, int]]:
    match = _VERSION_RE.match(version.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def compare_versions(current: str, latest: str) -> bool:
    """True when ``latest`` is strictly newer than ``current`` (AC-007).

    Unparseable versions (including dev builds) never report an update.
    """
    current_parts = _parse(current)
    latest_parts = _parse(latest)
    if current_parts is None or latest_parts is None:
        return False
    return latest_parts > current_parts


async def _fetch_latest_release() -> dict[str, Any]:
    """Latest non-draft, non-prerelease release from the GitHub API."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            RELEASES_URL, headers={"Accept": "application/vnd.github+json"}
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload


@dataclass(frozen=True)
class UpdateStatus:
    current: str
    latest: Optional[str]
    update_available: bool
    release_url: Optional[str]
    published_at: Optional[str]
    checked_at: Optional[datetime]


async def get_update_status(current: str) -> UpdateStatus:
    """Compare ``current`` against the latest release, using the cache (AC-006)."""
    settings = get_settings()
    if not settings.update_check_enabled:
        return UpdateStatus(current, None, False, None, None, None)

    ttl = timedelta(seconds=settings.update_check_ttl_seconds)
    now = utc_now()
    checked_at = _cache.get("checked_at")
    if checked_at is None or now - checked_at > ttl:
        try:
            _cache["release"] = await _fetch_latest_release()
        except Exception as error:  # noqa: BLE001 — degrade, never surface
            logger.debug("Update check failed: %s", error)
            _cache.setdefault("release", None)  # keep stale data if we had any
        _cache["checked_at"] = now

    release = _cache.get("release")
    if not release or not release.get("tag_name"):
        return UpdateStatus(current, None, False, None, None, _cache.get("checked_at"))

    latest = str(release["tag_name"]).lstrip("v")
    return UpdateStatus(
        current=current,
        latest=latest,
        update_available=compare_versions(current, latest),
        release_url=release.get("html_url"),
        published_at=release.get("published_at"),
        checked_at=_cache.get("checked_at"),
    )
