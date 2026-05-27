from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.auth_controller import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.business_monitor import BadCaseItem, BadCasesResponse, MonitorStatsResponse, PieStats
from app.services.business_monitor_service import BusinessMonitorService

router = APIRouter(prefix="/api/monitor", tags=["business-monitor"])


@router.get("/stats", response_model=MonitorStatsResponse)
async def get_monitor_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    svc = BusinessMonitorService(db)
    data = await svc.build_stats(current_user.id)
    pie = PieStats(**data["pie"])
    return MonitorStatsResponse(
        latency_24h=data["latency_24h"],
        low_confidence_task_ids=data["low_confidence_task_ids"],
        pie=pie,
    )


@router.get("/bad-cases", response_model=BadCasesResponse)
async def get_bad_cases(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    svc = BusinessMonitorService(db)
    items = await svc.list_bad_cases(current_user.id, request=request)
    return BadCasesResponse(items=[BadCaseItem.model_validate(x) for x in items])
