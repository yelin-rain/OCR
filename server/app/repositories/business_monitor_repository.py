from datetime import datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OCRTask, TaskStatus
from app.models.business_monitor import ErrorLog, OCRRunMetric


class BusinessMonitorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete_for_task(self, task_id: int) -> None:
        """删除任务关联的业务监控记录，避免外键阻止删除 ocr_tasks。"""
        await self.session.execute(
            delete(OCRRunMetric).where(OCRRunMetric.task_id == task_id)
        )
        await self.session.execute(
            delete(ErrorLog).where(ErrorLog.task_id == task_id)
        )

    async def add_error_log(
        self,
        error_type: str,
        message: str,
        detail: str | None,
        task_id: int | None,
        user_id: int | None,
    ) -> ErrorLog:
        row = ErrorLog(
            error_type=error_type,
            message=message,
            detail=detail,
            task_id=task_id,
            user_id=user_id,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def upsert_upload_metric(
        self,
        task_id: int,
        owner_id: int,
        http_latency_ms: float | None,
        image_size_bytes: int,
    ) -> OCRRunMetric:
        result = await self.session.execute(select(OCRRunMetric).where(OCRRunMetric.task_id == task_id))
        row = result.scalars().first()
        if row:
            row.http_latency_ms = http_latency_ms
            row.image_size_bytes = image_size_bytes
            row.owner_id = owner_id
            row.updated_at = datetime.utcnow()
        else:
            row = OCRRunMetric(
                task_id=task_id,
                owner_id=owner_id,
                http_latency_ms=http_latency_ms,
                image_size_bytes=image_size_bytes,
            )
            self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_inference_metric(
        self,
        task_id: int,
        owner_id: int | None,
        inference_ms: float | None,
        avg_confidence: float | None,
        image_width: int | None,
        image_height: int | None,
    ) -> None:
        result = await self.session.execute(select(OCRRunMetric).where(OCRRunMetric.task_id == task_id))
        row = result.scalars().first()
        if not row:
            row = OCRRunMetric(task_id=task_id, owner_id=owner_id)
            self.session.add(row)
        else:
            if owner_id is not None:
                row.owner_id = owner_id
        row.inference_ms = inference_ms
        row.avg_confidence = avg_confidence
        row.image_width = image_width
        row.image_height = image_height
        row.updated_at = datetime.utcnow()
        await self.session.commit()

    async def hourly_inference_avg_24h(self, owner_id: int) -> list[dict]:
        """近 24 小时按小时聚合平均推理耗时（仅已完成任务）。"""
        since = datetime.utcnow() - timedelta(hours=24)
        hour_bucket = func.date_trunc("hour", OCRTask.completed_at).label("bucket")
        stmt = (
            select(
                hour_bucket,
                func.avg(OCRTask.inference_ms).label("avg_ms"),
                func.count(OCRTask.id).label("cnt"),
            )
            .where(
                OCRTask.owner_id == owner_id,
                OCRTask.status == TaskStatus.COMPLETED,
                OCRTask.completed_at.is_not(None),
                OCRTask.completed_at >= since,
                OCRTask.inference_ms.is_not(None),
            )
            .group_by(hour_bucket)
            .order_by(hour_bucket)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "hour": r.bucket.strftime("%m-%d %H:00") if r.bucket else "",
                "avg_inference_ms": round(float(r.avg_ms), 2) if r.avg_ms is not None else 0.0,
                "count": int(r.cnt or 0),
            }
            for r in rows
        ]

    async def low_confidence_task_ids(self, owner_id: int, limit: int = 50) -> list[int]:
        stmt = (
            select(OCRTask.id)
            .where(
                OCRTask.owner_id == owner_id,
                OCRTask.status == TaskStatus.COMPLETED,
                OCRTask.avg_confidence.is_not(None),
                OCRTask.avg_confidence < 0.8,
            )
            .order_by(OCRTask.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [int(x[0]) for x in result.all()]

    async def status_counts_24h(self, owner_id: int) -> dict[str, int]:
        since = datetime.utcnow() - timedelta(hours=24)
        stmt = (
            select(OCRTask.status, func.count(OCRTask.id))
            .where(OCRTask.owner_id == owner_id, OCRTask.created_at >= since)
            .group_by(OCRTask.status)
        )
        result = await self.session.execute(stmt)
        counts: dict[str, int] = {
            "COMPLETED": 0,
            "FAILED": 0,
            "PENDING": 0,
            "PROCESSING": 0,
        }
        for status, cnt in result.all():
            counts[status.value] = int(cnt)
        total = sum(counts.values())
        return {"counts": counts, "total": total}

    async def list_bad_case_tasks(self, owner_id: int, limit: int = 30) -> list[OCRTask]:
        """识别不佳：置信度 < 0.8 的已完成，或失败任务。"""
        stmt = (
            select(OCRTask)
            .where(
                OCRTask.owner_id == owner_id,
                or_(
                    and_(
                        OCRTask.status == TaskStatus.COMPLETED,
                        OCRTask.avg_confidence.is_not(None),
                        OCRTask.avg_confidence < 0.8,
                    ),
                    OCRTask.status == TaskStatus.FAILED,
                ),
            )
            .order_by(OCRTask.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
