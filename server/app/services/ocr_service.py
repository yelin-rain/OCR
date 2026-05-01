from sqlalchemy.ext.asyncio import AsyncSession
from app.models import OCRTask, TaskStatus
from app.providers.storage_provider import storage_provider
from app.providers.ocr_provider_factory import get_ocr_provider
from app.repositories.ocr_task_repository import OCRTaskRepository
import uuid
import os
import json
from datetime import datetime, timedelta
import time
from PIL import Image
import io


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
        if task:
            try:
                storage_provider.delete_file(task.file_path)
            except Exception as e:
                print(f"Error deleting file from MinIO: {e}")
            
            await self.task_repo.delete(task)
        return task

    @staticmethod
    async def process_task_logic(task_id: int):
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.core.config import settings
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

                try:
                    started = time.perf_counter()
                    file_data = storage_provider.download_file(task.file_path)
                    img = Image.open(io.BytesIO(file_data))
                    task.image_width = int(img.width)
                    task.image_height = int(img.height)
                    processed_data = image_processor.process_image(file_data)
                    print(f"Image processed. Original size: {len(file_data)} bytes -> Processed: {len(processed_data)} bytes")

                    ocr_provider = get_ocr_provider()
                    api_result = await ocr_provider.ocr_general_basic(processed_data)
                    inference_ms = (time.perf_counter() - started) * 1000.0
                    OCRService._mark_task_completed(task, api_result, inference_ms)
                except Exception as e:
                    print(f"Error processing task {task_id}: {e}")
                    OCRService._mark_task_failed(task, str(e))
                
                await session.commit()
        finally:
            await engine.dispose()

    @staticmethod
    def _mark_task_completed(task: OCRTask, api_result: dict, inference_ms: float | None = None) -> None:
        task.result = json.dumps(api_result, ensure_ascii=False)
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.inference_ms = float(inference_ms) if inference_ms is not None else None
        task.model_version = str(api_result.get("model_version") or "official-PP-OCRv4")
        words = api_result.get("words_result", []) if isinstance(api_result, dict) else []
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
        task.status = TaskStatus.FAILED
        task.result = json.dumps({"error": error_message}, ensure_ascii=False)
