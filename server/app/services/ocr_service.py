from sqlalchemy.ext.asyncio import AsyncSession
from app.models import OCRTask, TaskStatus
from app.providers.storage_provider import storage_provider
from app.providers.ocr_provider_factory import get_ocr_provider
from app.repositories.ocr_task_repository import OCRTaskRepository
import uuid
import os
import json
from datetime import datetime


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
                    file_data = storage_provider.download_file(task.file_path)
                    processed_data = image_processor.process_image(file_data)
                    print(f"Image processed. Original size: {len(file_data)} bytes -> Processed: {len(processed_data)} bytes")

                    ocr_provider = get_ocr_provider()
                    api_result = await ocr_provider.ocr_general_basic(processed_data)
                    OCRService._mark_task_completed(task, api_result)
                except Exception as e:
                    print(f"Error processing task {task_id}: {e}")
                    OCRService._mark_task_failed(task, str(e))
                
                await session.commit()
        finally:
            await engine.dispose()

    @staticmethod
    def _mark_task_completed(task: OCRTask, api_result: dict) -> None:
        task.result = json.dumps(api_result, ensure_ascii=False)
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()

    @staticmethod
    def _mark_task_failed(task: OCRTask, error_message: str) -> None:
        task.status = TaskStatus.FAILED
        task.result = json.dumps({"error": error_message}, ensure_ascii=False)
