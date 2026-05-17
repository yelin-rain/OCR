from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.auth_controller import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.monitoring import BackupRecordEntry, BackupTriggerResponse, MonitoringSummary, SystemLogEntry
from app.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/summary", response_model=MonitoringSummary)
async def monitoring_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    svc = MonitoringService(db)
    data = await svc.get_summary()
    return MonitoringSummary.model_validate(data)


@router.get("/logs", response_model=list[SystemLogEntry])
async def monitoring_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    level: str | None = Query(None, description="INFO | WARNING | ERROR"),
):
    svc = MonitoringService(db)
    rows = await svc.list_logs(limit=limit, level=level)
    return [SystemLogEntry.model_validate(r) for r in rows]


@router.post("/backup", response_model=BackupTriggerResponse)
async def trigger_backup(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    svc = MonitoringService(db)
    ok, message, rec = await svc.run_database_backup(current_user.id)
    entry = BackupRecordEntry.model_validate(rec) if rec else None
    return BackupTriggerResponse(success=ok, message=message, record=entry)
