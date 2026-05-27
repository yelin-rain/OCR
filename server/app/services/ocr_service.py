import asyncio
import io
import json
import os
import time
import uuid
from datetime import datetime, timedelta

from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import OCRTask, TaskStatus
from app.providers.ocr_provider_factory import get_ocr_provider
from app.providers.storage_provider import storage_provider
from app.repositories.ocr_task_repository import OCRTaskRepository
from app.repositories.business_monitor_repository import BusinessMonitorRepository
from app.services.business_monitor_service import BusinessMonitorService
from app.services.monitoring_service import log_system_event_sync
from app.models.monitoring import LogLevel
from app.core.post_process import (
    join_words_result_to_raw_string,
    process_crnn_output,
    sync_words_result_with_processed,
)


class OCRService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_repo = OCRTaskRepository(db)

    async def create_task(self, file_content: bytes, filename: str, content_type: str, user_id: int) -> OCRTask:
        extension = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{extension}"
        storage_provider.upload_file(file_content, unique_filename, content_type)

        new_task = OCRTask(
            filename=filename,
            file_path=unique_filename,
            owner_id=user_id
        )
        return await self.task_repo.create(new_task)

    async def get_task(self, task_id: int, user_id: int = None) -> OCRTask | None:
        if user_id:
            return await self.task_repo.get_by_id_for_user(task_id, user_id)
        return await self.task_repo.get_by_id(task_id)

    async def list_tasks(self, skip: int = 0, limit: int = 20, user_id: int = None) -> list[OCRTask]:
        if user_id:
            return await self.task_repo.list_for_user(user_id, skip, limit)
        return await self.task_repo.list_all(skip, limit)

    async def list_user_history(
        self,
        user_id: int,
        keyword: str | None = None,
        days: int = 7,
        skip: int = 0,
        limit: int = 50,
    ) -> list[OCRTask]:
        return await self.task_repo.list_history_for_user(
            user_id=user_id,
            keyword=keyword,
            days=days,
            skip=skip,
            limit=limit,
        )

    async def save_corrections(
        self,
        task_id: int,
        corrections: list[dict],
        user_id: int | None = None,
    ) -> OCRTask | None:
        task = await self.get_task(task_id, user_id)
        if not task:
            return None
        task.correction_log = json.dumps(corrections, ensure_ascii=False)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_dashboard_analytics(self, user_id: int, days: int = 7) -> dict:
        tasks = await self.task_repo.list_history_for_user(user_id=user_id, days=days, limit=500)
        now = datetime.utcnow()
        trend: dict[str, list[float]] = {}
        total = len(tasks)
        failed = 0
        confidence_bins = {"gt90": 0, "70to90": 0, "lt70": 0, "unknown": 0}
        for task in tasks:
            day = task.created_at.strftime("%m-%d")
            if task.inference_ms is not None:
                trend.setdefault(day, []).append(float(task.inference_ms))
            if task.status == TaskStatus.FAILED:
                failed += 1
            if task.avg_confidence is None:
                confidence_bins["unknown"] += 1
            elif task.avg_confidence > 0.9:
                confidence_bins["gt90"] += 1
            elif task.avg_confidence >= 0.7:
                confidence_bins["70to90"] += 1
            else:
                confidence_bins["lt70"] += 1
        trend_points = []
        for i in range(days - 1, -1, -1):
            d = (now - timedelta(days=i)).date()
            k = d.strftime("%m-%d")
            vals = trend.get(k, [])
            trend_points.append(
                {"date": k, "avg_inference_ms": round(sum(vals) / len(vals), 2) if vals else 0.0}
            )
        return {
            "trend": trend_points,
            "confidence_distribution": confidence_bins,
            "failure_ratio": round((failed / total) * 100, 2) if total else 0.0,
            "total_tasks": total,
            "failed_tasks": failed,
        }

    async def delete_task(self, task_id: int, user_id: int = None) -> OCRTask | None:
        task = await self.get_task(task_id, user_id)
        if not task:
            return None

        file_path = task.file_path
        bm_repo = BusinessMonitorRepository(self.db)
        await bm_repo.delete_for_task(task_id)
        await self.task_repo.delete(task, commit=False)
        await self.db.commit()

        try:
            storage_provider.delete_file(file_path)
        except Exception as e:
            print(f"Error deleting file from MinIO: {e}")

        return task

    @staticmethod
    async def process_task_logic(task_id: int, use_local_models: bool | None = None):
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.core.image_processor import image_processor

        engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        LocalSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with LocalSession() as session:
                task_repo = OCRTaskRepository(session)
                task = await task_repo.get_by_id(task_id)
                if not task:
                    print(f"Task {task_id} not found during processing")
                    return

                task.status = TaskStatus.PROCESSING
                await session.commit()

                bm = BusinessMonitorService(session)

                def _classify_error(exc: BaseException) -> tuple[str, str]:
                    if isinstance(exc, asyncio.TimeoutError):
                        return "MODEL_TIMEOUT", "OCR 推理超时"
                    if isinstance(exc, UnidentifiedImageError):
                        return "IMAGE_CORRUPT", "无法识别图片格式或文件已损坏"
                    s = str(exc).lower()
                    if "timeout" in s or "timed out" in s:
                        return "MODEL_TIMEOUT", "模型或网络超时"
                    if "identify" in s or "cannot identify" in s or "truncated" in s:
                        return "IMAGE_CORRUPT", "图片数据不完整或已损坏"
                    if any(k in s for k in ("paddle", "model load", "初始化")):
                        return "MODEL_LOAD_ERROR", "模型加载或初始化异常"
                    return "OCR_ERROR", "识别过程异常"

                try:
                    started = time.perf_counter()
                    file_data = storage_provider.download_file(task.file_path)
                    try:
                        img = Image.open(io.BytesIO(file_data))
                        task.image_width = int(img.width)
                        task.image_height = int(img.height)
                    except (UnidentifiedImageError, OSError) as e:
                        await bm.log_error(
                            "IMAGE_CORRUPT",
                            "打开图片失败",
                            str(e)[:2000],
                            task.id,
                            task.owner_id,
                        )
                        OCRService._mark_task_failed(task, str(e))
                        await session.commit()
                        return

                    processed_data = image_processor.process_image(file_data)
                    proc_img = Image.open(io.BytesIO(processed_data))
                    proc_w, proc_h = int(proc_img.width), int(proc_img.height)
                    print(f"Image processed. Original size: {len(file_data)} bytes -> Processed: {len(processed_data)} bytes")

                    ocr_provider = get_ocr_provider()
                    try:
                        api_result = await asyncio.wait_for(
                            ocr_provider.ocr_general_basic(
                                processed_data,
                                use_local_models=use_local_models,
                            ),
                            timeout=settings.OCR_INFERENCE_TIMEOUT_SEC,
                        )
                    except asyncio.TimeoutError:
                        await bm.log_error(
                            "MODEL_TIMEOUT",
                            "OCR 推理超时",
                            f"超过 {settings.OCR_INFERENCE_TIMEOUT_SEC} 秒",
                            task.id,
                            task.owner_id,
                        )
                        OCRService._mark_task_failed(task, "OCR inference timeout")
                        await session.commit()
                        return

                    words = api_result.get("words_result") if isinstance(api_result, dict) else []
                    if (
                        isinstance(words, list)
                        and task.image_width
                        and task.image_height
                    ):
                        image_processor.map_words_result_to_original(
                            words,
                            task.image_width,
                            task.image_height,
                            proc_w,
                            proc_h,
                        )

                    inference_ms = (time.perf_counter() - started) * 1000.0
                    OCRService._mark_task_completed(task, api_result, inference_ms)
                    await bm.record_inference_complete(
                        task.id,
                        task.owner_id,
                        task.inference_ms,
                        task.avg_confidence,
                        task.image_width,
                        task.image_height,
                    )
                except Exception as e:
                    print(f"Error processing task {task_id}: {e}")
                    et, title = _classify_error(e)
                    await bm.log_error(et, title, str(e)[:4000], task.id, task.owner_id)
                    OCRService._mark_task_failed(task, str(e))

                await session.commit()
        finally:
            await engine.dispose()

    @staticmethod
    def _mark_task_completed(task: OCRTask, api_result: dict, inference_ms: float | None = None) -> None:
        words = api_result.get("words_result", []) if isinstance(api_result, dict) else []
        raw_joined = join_words_result_to_raw_string(words if isinstance(words, list) else [])
        original_text, processed_text, post_corrections = process_crnn_output(raw_joined)
        api_result["original_text"] = original_text
        api_result["processed_text"] = processed_text
        api_result["full_text"] = processed_text
        if post_corrections:
            api_result["post_corrections"] = post_corrections
        if isinstance(words, list) and words:
            sync_words_result_with_processed(words, original_text, processed_text)
            api_result["words_result"] = words

        task.result = json.dumps(api_result, ensure_ascii=False)
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.inference_ms = float(inference_ms) if inference_ms is not None else None
        task.model_version = str(api_result.get("model_version") or "official-PP-OCRv4")
        scores = []
        for item in words if isinstance(words, list) else []:
            try:
                s = float(item.get("probability", 0))
                scores.append(s)
            except Exception:
                continue
        task.avg_confidence = (sum(scores) / len(scores)) if scores else None

    @staticmethod
    def _mark_task_failed(task: OCRTask, error_message: str) -> None:
        log_system_event_sync(
            LogLevel.ERROR.value,
            "ocr_worker",
            f"OCR 任务失败 task_id={task.id}",
            detail=error_message[:4000],
        )
        task.status = TaskStatus.FAILED
        task.result = json.dumps({"error": error_message}, ensure_ascii=False)
