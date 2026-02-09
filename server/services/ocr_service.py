from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.task import OCRTask, TaskStatus
from schemas.task import TaskCreate, TaskResponse
from providers.storage_provider import storage_provider
from providers.baidu_provider import baidu_provider
from core.database import AsyncSessionLocal
import uuid
import os
import json
import logging

class OCRService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(self, file_content: bytes, filename: str, content_type: str, user_id: int) -> OCRTask:
        # 上传到minio
        extension = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{extension}"
        storage_provider.upload_file(file_content, unique_filename, content_type)

        # 创建DB入口
        new_task = OCRTask(
            filename=filename,
            file_path=unique_filename,
            owner_id=user_id
        )
        self.db.add(new_task)
        await self.db.commit()
        await self.db.refresh(new_task)
        
        return new_task

    async def get_task(self, task_id: int, user_id: int = None) -> OCRTask:
        if user_id:
            query = select(OCRTask).where(OCRTask.id == task_id, OCRTask.owner_id == user_id)
        else:
            query = select(OCRTask).where(OCRTask.id == task_id)
            
        result = await self.db.execute(query)
        task = result.scalars().first()
        return task

    async def list_tasks(self, skip: int = 0, limit: int = 20, user_id: int = None) -> list[OCRTask]:
        query = select(OCRTask).order_by(OCRTask.created_at.desc()).offset(skip).limit(limit)
        if user_id:
            query = query.where(OCRTask.owner_id == user_id)
            
        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_task(self, task_id: int, user_id: int = None):
        task = await self.get_task(task_id, user_id)
        if task:
            try:
                storage_provider.delete_file(task.file_path)
            except Exception as e:
                print(f"Error deleting file from MinIO: {e}")
            
            await self.db.delete(task)
            await self.db.commit()
        return task

    @staticmethod
    async def process_task_logic(task_id: int):
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from core.config import settings
        
        # 创建新的session
        engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        LocalSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with LocalSession() as session:
                # 查询任务
                result = await session.execute(select(OCRTask).where(OCRTask.id == task_id))
                task = result.scalars().first()
                if not task:
                    print(f"Task {task_id} not found during processing")
                    return

                # 更新状态为processing
                task.status = TaskStatus.PROCESSING
                await session.commit()

                try:
                    # 下载文件
                    file_data = storage_provider.download_file(task.file_path)

                    # 调用百度ocr
                    api_result = await baidu_provider.ocr_general_basic(file_data)
                    
                    # 保存结果
                    task.result = json.dumps(api_result, ensure_ascii=False)
                    task.status = TaskStatus.COMPLETED
                    from datetime import datetime
                    task.completed_at = datetime.utcnow()
                    
                except Exception as e:
                    print(f"Error processing task {task_id}: {e}")
                    task.status = TaskStatus.FAILED
                    task.result = json.dumps({"error": str(e)})
                
                await session.commit()
        finally:
            await engine.dispose()
