from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from typing import Annotated
import time

from app.controllers.auth_controller import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import TaskStatus, User
from app.schemas.task import TaskResponse, TaskCorrectionRequest
from app.services.ocr_service import OCRService
from app.services.business_monitor_service import BusinessMonitorService
from tasks import process_ocr_task
from app.providers.storage_provider import storage_provider
import json

router = APIRouter(prefix="/ocr", tags=["ocr"])


def _build_task_response(task) -> TaskResponse:
    response = TaskResponse.model_validate(task)
    response.file_url = storage_provider.get_file_url(task.file_path)
    if task.result:
        try:
            payload = json.loads(task.result)
            if isinstance(payload, dict):
                response.original_text = payload.get("original_text")
                response.processed_text = payload.get("processed_text")
        except json.JSONDecodeError:
            pass
    return response


async def _get_user_task_or_404(service: OCRService, task_id: int, user_id: int):
    task = await service.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/task", response_model=TaskResponse)
async def create_ocr_task(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    file_content = await file.read()
    http_ms = None
    t0 = getattr(request.state, "ocr_mon_started", None)
    if t0 is not None:
        http_ms = (time.perf_counter() - t0) * 1000.0

    new_task = await service.create_task(file_content, file.filename, file.content_type, current_user.id)
    bm = BusinessMonitorService(db)
    await bm.record_upload(new_task.id, current_user.id, http_ms, len(file_content))
    celery_task = process_ocr_task.delay(new_task.id)

    new_task.celery_task_id = celery_task.id
    await db.commit()

    return _build_task_response(new_task)

@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int, 
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    task = await _get_user_task_or_404(service, task_id, current_user.id)
    return _build_task_response(task)


@router.get("/task/{task_id}/status")
async def get_task_status(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    task = await _get_user_task_or_404(service, task_id, current_user.id)
    celery_state = None
    if task.celery_task_id:
        from celery_worker import celery_app
        celery_state = celery_app.AsyncResult(task.celery_task_id).state
    return {
        "task_id": task.id,
        "status": task.status,
        "celery_task_id": task.celery_task_id,
        "celery_state": celery_state,
    }

@router.post("/task/{task_id}/stop")
async def stop_ocr_task(
    task_id: int, 
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    task = await _get_user_task_or_404(service, task_id, current_user.id)
        
    if task.celery_task_id and task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
        from celery_worker import celery_app
        celery_app.control.revoke(task.celery_task_id, terminate=True)
        task.status = TaskStatus.FAILED
        task.result = json.dumps({"error": "Task stopped by user"})
        await db.commit()
        
    return {"message": "Task stopped"}

@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0, 
    limit: int = 20, 
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    tasks = await service.list_tasks(skip, limit, current_user.id)
    return [_build_task_response(task) for task in tasks]


@router.get("/history", response_model=list[TaskResponse])
async def list_history(
    current_user: Annotated[User, Depends(get_current_user)],
    keyword: str | None = None,
    days: int = 7,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    service = OCRService(db)
    tasks = await service.list_user_history(
        user_id=current_user.id,
        keyword=keyword,
        days=days,
        skip=skip,
        limit=limit,
    )
    return [_build_task_response(task) for task in tasks]


@router.get("/analytics/dashboard")
async def get_dashboard_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = 7,
    db: AsyncSession = Depends(get_db),
):
    service = OCRService(db)
    return await service.get_dashboard_analytics(current_user.id, days=days)


@router.post("/task/{task_id}/correction", response_model=TaskResponse)
async def save_task_correction(
    task_id: int,
    payload: TaskCorrectionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    service = OCRService(db)
    updated = await service.save_corrections(
        task_id=task_id,
        corrections=[item.model_dump() for item in payload.corrections],
        user_id=current_user.id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return _build_task_response(updated)

@router.delete("/task/{task_id}")
async def delete_ocr_task(
    task_id: int, 
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    result = await service.delete_task(task_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted"}
