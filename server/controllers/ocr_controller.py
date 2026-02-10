from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Annotated
from models import User
from controllers.auth_controller import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from models import OCRTask, TaskStatus, User
from schemas.task import TaskResponse
from services.ocr_service import OCRService
from tasks import process_ocr_task
from providers.storage_provider import storage_provider
import json

router = APIRouter(prefix="/ocr", tags=["ocr"])

@router.post("/task", response_model=TaskResponse)
async def create_ocr_task(
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    
    # 读文件内容
    file_content = await file.read()
    
    # 执行create任务
    new_task = await service.create_task(file_content, file.filename, file.content_type, current_user.id)
    
    # 触发celery任务
    celery_task = process_ocr_task.delay(new_task.id)
    
    # 更新celery任务id
    new_task.celery_task_id = celery_task.id
    await db.commit()

    # Generate file_url for response
    response = TaskResponse.model_validate(new_task)
    response.file_url = storage_provider.get_file_url(new_task.file_path)

    return response

@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int, 
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    task = await service.get_task(task_id, current_user.id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 生成预览url
    task_response = TaskResponse.model_validate(task)
    task_response.file_url = storage_provider.get_file_url(task.file_path)
    
    return task_response

@router.post("/task/{task_id}/stop")
async def stop_ocr_task(
    task_id: int, 
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    task = await service.get_task(task_id, current_user.id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
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
    
    # Populate file_url for each task
    response_list = []
    for task in tasks:
        task_res = TaskResponse.model_validate(task)
        task_res.file_url = storage_provider.get_file_url(task.file_path)
        response_list.append(task_res)
        
    return response_list

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
