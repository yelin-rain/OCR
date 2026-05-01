from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Annotated
from app.controllers.auth_controller import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import TaskStatus, User
from app.schemas.task import TaskResponse
from app.services.ocr_service import OCRService
from tasks import process_ocr_task
from app.providers.storage_provider import storage_provider
import json

router = APIRouter(prefix="/ocr", tags=["ocr"])


def _build_task_response(task) -> TaskResponse:
    response = TaskResponse.model_validate(task)
    response.file_url = storage_provider.get_file_url(task.file_path)
    return response


async def _get_user_task_or_404(service: OCRService, task_id: int, user_id: int):
    task = await service.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/task", response_model=TaskResponse)
async def create_ocr_task(
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    file_content = await file.read()

    new_task = await service.create_task(file_content, file.filename, file.content_type, current_user.id)
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
