from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import DataBackupRecord, LogLevel, SystemLog


class MonitoringRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_log(
        self,
        level: str,
        source: str,
        message: str,
        detail: str | None = None,
        path: str | None = None,
        user_id: int | None = None,
    ) -> SystemLog:
        row = SystemLog(
            level=level,
            source=source,
            message=message,
            detail=detail,
            path=path,
            user_id=user_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def list_logs(self, limit: int = 50, level: str | None = None) -> list[SystemLog]:
        q = select(SystemLog)
        if level:
            q = q.where(SystemLog.level == level)
        q = q.order_by(SystemLog.created_at.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def count_since(self, level: LogLevel | str, since: datetime) -> int:
        lvl = level.value if isinstance(level, LogLevel) else level
        q = select(func.count()).select_from(SystemLog).where(
            SystemLog.level == lvl,
            SystemLog.created_at >= since,
        )
        result = await self.db.execute(q)
        return int(result.scalar() or 0)

    async def count_all_since(self, since: datetime) -> int:
        q = select(func.count()).select_from(SystemLog).where(SystemLog.created_at >= since)
        result = await self.db.execute(q)
        return int(result.scalar() or 0)

    async def add_backup_record(
        self,
        filename: str,
        file_path: str,
        size_bytes: int,
        success: bool,
        error_message: str | None,
        created_by_user_id: int | None,
    ) -> DataBackupRecord:
        row = DataBackupRecord(
            filename=filename,
            file_path=file_path,
            size_bytes=size_bytes,
            success=success,
            error_message=error_message,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def latest_backup(self) -> DataBackupRecord | None:
        q = select(DataBackupRecord).order_by(DataBackupRecord.created_at.desc()).limit(1)
        result = await self.db.execute(q)
        return result.scalars().first()
