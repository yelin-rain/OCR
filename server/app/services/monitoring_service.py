import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.monitoring import LogLevel, SystemLog
from app.models.task import OCRTask
from app.models.user import User
from app.repositories.monitoring_repository import MonitoringRepository

logger = logging.getLogger(__name__)


def log_system_event_sync(
    level: str,
    source: str,
    message: str,
    detail: str | None = None,
    path: str | None = None,
    user_id: int | None = None,
) -> None:
    """供 Celery / 同步上下文写入 system_logs，使用与 API 相同的 asyncpg 连接。"""

    async def _insert() -> None:
        async with AsyncSessionLocal() as session:
            session.add(
                SystemLog(
                    level=level,
                    source=source,
                    message=message,
                    detail=detail,
                    path=path,
                    user_id=user_id,
                )
            )
            await session.commit()

    try:
        asyncio.run(_insert())
    except RuntimeError as e:
        if "asyncio.run()" in str(e) or "running event loop" in str(e).lower():
            logger.warning("log_system_event_sync skipped (nested event loop): %s", e)
        else:
            logger.warning("log_system_event_sync failed: %s", e)
    except Exception as e:
        logger.warning("log_system_event_sync failed: %s", e)


class MonitoringService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MonitoringRepository(db)

    async def log(
        self,
        level: LogLevel | str,
        source: str,
        message: str,
        detail: str | None = None,
        path: str | None = None,
        user_id: int | None = None,
    ) -> None:
        lvl = level.value if isinstance(level, LogLevel) else level
        await self.repo.add_log(
            level=lvl,
            source=source,
            message=message,
            detail=detail,
            path=path,
            user_id=user_id,
        )
        line = f"[{source}] {message}"
        if detail:
            line += f" | {detail[:500]}"
        if lvl == LogLevel.ERROR.value:
            logger.error(line)
        elif lvl == LogLevel.WARNING.value:
            logger.warning(line)
        else:
            logger.info(line)

    async def get_summary(self) -> dict:
        since = datetime.utcnow() - timedelta(hours=24)
        errors = await self.repo.count_since(LogLevel.ERROR, since)
        warnings = await self.repo.count_since(LogLevel.WARNING, since)
        total = await self.repo.count_all_since(since)
        last = await self.repo.latest_backup()
        return {
            "errors_last_24h": errors,
            "warnings_last_24h": warnings,
            "total_logs_last_24h": total,
            "last_backup_at": last.created_at if last else None,
            "last_backup_ok": last.success if last else None,
            "backup_dir": settings.DATA_BACKUP_DIR,
            "app_log_file": settings.APP_LOG_FILE,
        }

    async def list_logs(self, limit: int = 50, level: str | None = None):
        return await self.repo.list_logs(limit=limit, level=level)

    async def run_database_backup(self, user_id: int | None) -> tuple[bool, str, object | None]:
        os.makedirs(settings.DATA_BACKUP_DIR, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        sql_name = f"pg_dump_{ts}.sql"
        sql_path = os.path.join(settings.DATA_BACKUP_DIR, sql_name)

        env = os.environ.copy()
        env["PGPASSWORD"] = settings.POSTGRES_PASSWORD

        cmd = [
            "pg_dump",
            "-h",
            settings.POSTGRES_HOST,
            "-p",
            str(settings.POSTGRES_PORT),
            "-U",
            settings.POSTGRES_USER,
            "-d",
            settings.POSTGRES_DB,
            "-f",
            sql_path,
            "--no-owner",
        ]
        try:
            subprocess.run(
                cmd,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError:
            msg = await self._fallback_json_backup(ts, user_id, "未找到 pg_dump 可执行文件（请安装 PostgreSQL 客户端或配置 PATH）")
            rec = await self.repo.latest_backup()
            return (True, msg, rec) if rec and rec.success else (False, msg, rec)
        except subprocess.CalledProcessError as e:
            err_txt = (e.stderr or e.stdout or str(e))[:2000]
            msg = await self._fallback_json_backup(ts, user_id, f"pg_dump 失败: {err_txt}")
            rec = await self.repo.latest_backup()
            return (True, msg, rec) if rec and rec.success else (False, msg, rec)
        except subprocess.TimeoutExpired:
            await self.log(LogLevel.ERROR, "backup", "pg_dump 超时", user_id=user_id)
            fail = await self.repo.add_backup_record(
                filename=sql_name,
                file_path=sql_path,
                size_bytes=0,
                success=False,
                error_message="timeout",
                created_by_user_id=user_id,
            )
            return False, "备份超时", fail

        size = os.path.getsize(sql_path)
        rec = await self.repo.add_backup_record(
            filename=sql_name,
            file_path=sql_path,
            size_bytes=size,
            success=True,
            error_message=None,
            created_by_user_id=user_id,
        )
        await self.log(
            LogLevel.INFO,
            "backup",
            f"数据库备份成功: {sql_name}",
            detail=json.dumps({"bytes": size}, ensure_ascii=False),
            user_id=user_id,
        )
        return True, "数据库备份成功（SQL 转储）", rec

    async def _fallback_json_backup(self, ts: str, user_id: int | None, reason: str) -> str:
        """使用异步会话读取库表（asyncpg），避免依赖 psycopg2 同步驱动。"""
        json_name = f"metadata_export_{ts}.json"
        json_path = os.path.join(settings.DATA_BACKUP_DIR, json_name)

        try:
            ru = await self.db.execute(select(User.id, User.username, User.email))
            users = [dict(m) for m in ru.mappings().all()]
            rt = await self.db.execute(
                select(
                    OCRTask.id,
                    OCRTask.filename,
                    OCRTask.status,
                    OCRTask.created_at,
                    OCRTask.owner_id,
                )
            )
            tasks = [dict(m) for m in rt.mappings().all()]
            payload = {
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "reason": reason,
                "users": users,
                "tasks": tasks,
            }
            Path(json_path).write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
            size = os.path.getsize(json_path)
            await self.repo.add_backup_record(
                filename=json_name,
                file_path=json_path,
                size_bytes=size,
                success=True,
                error_message=f"fallback: {reason[:500]}",
                created_by_user_id=user_id,
            )
            await self.log(
                LogLevel.WARNING,
                "backup",
                "已使用 JSON 元数据降级备份（不含对象存储文件与大字段原文）",
                detail=json.dumps({"file": json_name, "reason": reason[:500]}, ensure_ascii=False),
                user_id=user_id,
            )
            return "pg_dump 不可用或失败，已导出任务与用户元数据 JSON（与当前 API 使用同一数据库连接）。"
        except Exception as e:
            await self.log(LogLevel.ERROR, "backup", "降级备份失败", detail=str(e), user_id=user_id)
            await self.repo.add_backup_record(
                filename=json_name,
                file_path=json_path,
                size_bytes=0,
                success=False,
                error_message=str(e)[:2000],
                created_by_user_id=user_id,
            )
            return f"备份失败: {e}"
