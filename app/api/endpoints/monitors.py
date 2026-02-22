import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import SessionDep, ApiKeyDep
from app.models.monitor import SyncSourceMonitor
from app.schemas.monitor import MonitorCreate, MonitorUpdate, MonitorRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitors", tags=["monitors"])


@router.get(
    "",
    response_model=list[MonitorRead],
    summary="List sync source monitors",
)
async def list_monitors(session: SessionDep, api_key: ApiKeyDep):
    """List all configured sync source monitors."""
    statement = select(SyncSourceMonitor).order_by(SyncSourceMonitor.source_name)
    monitors = session.exec(statement).all()
    return monitors


@router.post(
    "",
    response_model=MonitorRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a sync source monitor",
)
async def create_monitor(data: MonitorCreate, session: SessionDep, api_key: ApiKeyDep):
    """Create a new sync source monitor for staleness detection."""
    # Check for duplicate source_name
    existing = session.exec(
        select(SyncSourceMonitor).where(
            SyncSourceMonitor.source_name == data.source_name
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Monitor for source '{data.source_name}' already exists",
        )

    monitor = SyncSourceMonitor(
        source_name=data.source_name,
        expected_interval_hours=data.expected_interval_hours,
        grace_multiplier=data.grace_multiplier,
        enabled=data.enabled,
    )
    session.add(monitor)
    session.commit()
    session.refresh(monitor)

    logger.info(
        "Monitor created",
        extra={
            "source_name": data.source_name,
            "interval_hours": data.expected_interval_hours,
        },
    )
    return monitor


@router.put(
    "/{monitor_id}",
    response_model=MonitorRead,
    summary="Update a sync source monitor",
)
async def update_monitor(
    monitor_id: UUID,
    data: MonitorUpdate,
    session: SessionDep,
    api_key: ApiKeyDep,
):
    """Update an existing sync source monitor."""
    monitor = session.get(SyncSourceMonitor, monitor_id)
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(monitor, key, value)
    monitor.updated_at = datetime.utcnow()

    session.add(monitor)
    session.commit()
    session.refresh(monitor)

    logger.info("Monitor updated", extra={"monitor_id": str(monitor_id)})
    return monitor


@router.delete(
    "/{monitor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a sync source monitor",
)
async def delete_monitor(monitor_id: UUID, session: SessionDep, api_key: ApiKeyDep):
    """Delete a sync source monitor."""
    monitor = session.get(SyncSourceMonitor, monitor_id)
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found",
        )

    session.delete(monitor)
    session.commit()

    logger.info("Monitor deleted", extra={"monitor_id": str(monitor_id)})
