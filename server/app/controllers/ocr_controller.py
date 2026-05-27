from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request, Query
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Annotated
import mimetypes
import time

from app.controllers.auth_controller import get_current_user
from app.core.security import verify_file_view_token
from app.utils.task_file_url import build_task_file_url
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import TaskStatus, User
from app.schemas.task import TaskResponse, TaskCorrectionRequest
from app.services.ocr_service import OCRService
from app.services.business_monitor_service import BusinessMonitorService
from tasks import process_ocr_task
from app.providers.storage_provider import storage_provider
from app.providers.local_ocr_provider import LocalOCRProvider
from app.core.config import settings
import json

router = APIRouter(prefix="/ocr", tags=["ocr"])
_optional_bearer = HTTPBearer(auto_error=False)


def _build_task_response(task, request: Request | None = None) -> TaskResponse:
    response = TaskResponse.model_validate(task)
    response.file_url = build_task_file_url(task, request=request)
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

@router.get("/task/{task_id}/file")
async def get_task_file(
    task_id: int,
    token: str | None = Query(None),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_optional_bearer)] = None,
    db: AsyncSession = Depends(get_db),
):
    """任务原图：支持 Bearer 或 ?token=（供 img 标签在局域网访问）。"""
    service = OCRService(db)
    user_id: int | None = None

    if token:
        try:
            user_id = verify_file_view_token(token, task_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid or expired file token")
    elif credentials is not None:
        try:
            user = await get_current_user(credentials.credentials, db)
            user_id = user.id
        except HTTPException:
            raise HTTPException(status_code=401, detail="Could not validate credentials")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    task = await service.get_task(task_id, user_id)
    if not task or not task.file_path:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        data = storage_provider.download_file(task.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    media_type, _ = mimetypes.guess_type(task.filename or "")
    return Response(
        content=data,
        media_type=media_type or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.get("/model-options")
async def get_model_options(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """识别页可选模型：官方 PP-OCRv4 与自训练 det/rec。"""
    local_available = LocalOCRProvider.local_models_available()
    default_local = bool(settings.USE_LOCAL_MODELS)
    return {
        "provider": settings.OCR_PROVIDER.lower().strip(),
        "default_use_local_models": default_local,
        "local_models_available": local_available,
        "modes": [
            {
                "id": "official",
                "use_local_models": False,
                "label": "官方模型",
                "description": "PaddleOCR PP-OCRv4 预训练权重",
            },
            {
                "id": "custom",
                "use_local_models": True,
                "label": "自训练模型",
                "description": "det_db_resnet50_cbam + rec_rare_2（SVTR）",
                "available": local_available,
            },
        ],
    }


@router.post("/task", response_model=TaskResponse)
async def create_ocr_task(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    use_local_models: bool | None = Query(
        default=None,
        description="True=自训练模型，False=官方 PP-OCRv4；省略则用服务端默认配置",
    ),
    db: AsyncSession = Depends(get_db),
):
    service = OCRService(db)
    file_content = await file.read()
    http_ms = None
    t0 = getattr(request.state, "ocr_mon_started", None)
    if t0 is not None:
        http_ms = (time.perf_counter() - t0) * 1000.0

    if settings.OCR_PROVIDER.lower().strip() != "local" and use_local_models is not None:
        raise HTTPException(
            status_code=400,
            detail="当前 OCR 提供方非 local，无法切换本地/官方模型",
        )
    if use_local_models and not LocalOCRProvider.local_models_available():
        raise HTTPException(
            status_code=400,
            detail="自训练模型文件不完整，请检查 inference_models 目录或改用官方模型",
        )

    resolved_local = (
        bool(settings.USE_LOCAL_MODELS) if use_local_models is None else bool(use_local_models)
    )

    new_task = await service.create_task(file_content, file.filename, file.content_type, current_user.id)
    bm = BusinessMonitorService(db)
    await bm.record_upload(new_task.id, current_user.id, http_ms, len(file_content))
    celery_task = process_ocr_task.delay(new_task.id, use_local_models=resolved_local)

    new_task.celery_task_id = celery_task.id
    await db.commit()

    return _build_task_response(new_task, request=request)

@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    task = await _get_user_task_or_404(service, task_id, current_user.id)
    return _build_task_response(task, request=request)


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
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0, 
    limit: int = 20, 
    db: AsyncSession = Depends(get_db)
):
    service = OCRService(db)
    tasks = await service.list_tasks(skip, limit, current_user.id)
    return [_build_task_response(task, request=request) for task in tasks]


@router.get("/history", response_model=list[TaskResponse])
async def list_history(
    request: Request,
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
    return [_build_task_response(task, request=request) for task in tasks]


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
    request: Request,
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
    return _build_task_response(updated, request=request)

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
