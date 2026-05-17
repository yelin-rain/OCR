from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from datetime import datetime, timedelta

from app.models import OCRTask


class OCRTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: OCRTask) -> OCRTask:
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: int) -> OCRTask | None:
        result = await self.session.execute(select(OCRTask).where(OCRTask.id == task_id))
        return result.scalars().first()

    async def get_by_id_for_user(self, task_id: int, user_id: int) -> OCRTask | None:
        result = await self.session.execute(
            select(OCRTask).where(OCRTask.id == task_id, OCRTask.owner_id == user_id)
        )
        return result.scalars().first()

    async def list_for_user(self, user_id: int, skip: int = 0, limit: int = 20) -> list[OCRTask]:
        result = await self.session.execute(
            select(OCRTask)
            .where(OCRTask.owner_id == user_id)
            .order_by(OCRTask.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def list_all(self, skip: int = 0, limit: int = 20) -> list[OCRTask]:
        result = await self.session.execute(
            select(OCRTask).order_by(OCRTask.created_at.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def delete(self, task: OCRTask, *, commit: bool = True) -> None:
        await self.session.delete(task)
        if commit:
            await self.session.commit()

    async def list_history_for_user(
        self,
        user_id: int,
        keyword: str | None = None,
        days: int = 7,
        skip: int = 0,
        limit: int = 50,
    ) -> list[OCRTask]:
        since = datetime.utcnow() - timedelta(days=max(1, days))
        stmt = (
            select(OCRTask)
            .where(
                and_(
                    OCRTask.owner_id == user_id,
                    OCRTask.created_at >= since,
                )
            )
            .order_by(OCRTask.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if keyword:
            kw = f"%{keyword}%"
            stmt = stmt.where(
                or_(
                    OCRTask.filename.ilike(kw),
                    OCRTask.result.ilike(kw),
                )
            )
        result = await self.session.execute(stmt)
        return result.scalars().all()
