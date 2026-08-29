"""Synthetic monitoring API (specs/insight-ui.md AC-002, AC-003)."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlmodel import col, func, select

from app.api.deps import SessionDep, require_role_or_api_key
from app.config import get_settings
from app.models.synthetic_check_config import SyntheticCheckConfig
from app.models.synthetic_check_result import SyntheticCheckResultRecord
from app.schemas.synthetic import SyntheticCheckRead, SyntheticStatus
from app.services.auth import ROLE_VIEWER
from app.services.synthetic_check import get_check_history, get_uptime_percentage
from app.utils import utc_now

router = APIRouter(
    prefix="/synthetic",
    tags=["synthetic"],
    dependencies=[Depends(require_role_or_api_key(ROLE_VIEWER))],
)

HISTORY_DEFAULT_LIMIT = 100
HISTORY_MAX_LIMIT = 500


@router.get(
    "/status",
    response_model=SyntheticStatus,
    summary="Synthetic monitoring liveness summary",
)
async def synthetic_status(session: SessionDep) -> SyntheticStatus:
    """Return enabled flag, latest result, and uptime over 24 h / 7 d."""
    config = session.get(SyntheticCheckConfig, 1)
    enabled = bool(config and config.enabled)
    interval = (
        config.interval_seconds
        if config
        else get_settings().synthetic_check_interval_seconds
    )

    latest = get_check_history(session, limit=1)
    last = latest[0] if latest else None

    if not enabled:
        status = "disabled"
    elif last is None:
        status = "unknown"
    else:
        status = last.status

    cutoff_24h = utc_now() - timedelta(hours=24)
    checks_24h = session.exec(
        select(func.count())
        .select_from(SyntheticCheckResultRecord)
        .where(col(SyntheticCheckResultRecord.checked_at) >= cutoff_24h)
    ).one()

    return SyntheticStatus(
        enabled=enabled,
        status=status,
        last_check_at=last.checked_at if last else None,
        last_latency_ms=last.latency_ms if last else None,
        interval_seconds=interval,
        uptime_24h_pct=get_uptime_percentage(session, hours=24),
        uptime_7d_pct=get_uptime_percentage(session, hours=24 * 7),
        checks_24h=int(checks_24h),
    )


@router.get(
    "/history",
    response_model=list[SyntheticCheckRead],
    summary="Recent synthetic check results, newest first",
)
async def synthetic_history(
    session: SessionDep,
    limit: int = Query(
        HISTORY_DEFAULT_LIMIT, ge=1, le=HISTORY_MAX_LIMIT, description="Max rows"
    ),
) -> list[SyntheticCheckRead]:
    """Return the most recent check results for the uptime timeline."""
    return [
        SyntheticCheckRead(
            checked_at=r.checked_at,
            status=r.status,
            latency_ms=r.latency_ms,
            error=r.error,
        )
        for r in get_check_history(session, limit=limit)
    ]
