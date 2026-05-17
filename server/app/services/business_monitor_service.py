import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import OCRTask, TaskStatus
from app.providers.storage_provider import storage_provider
from app.repositories.business_monitor_repository import BusinessMonitorRepository

logger = logging.getLogger(__name__)


def _result_text_preview(result_json: str | None, max_len: int = 400) -> str | None:
    if not result_json:
        return None
    try:
        data = json.loads(result_json)
        words = data.get("words_result")
        if isinstance(words, list):
            lines = [str(w.get("words", "")).strip() for w in words if isinstance(w, dict)]
            text = "\n".join(lines)[:max_len]
            return text or None
        if isinstance(data.get("full_text"), str):
            return data["full_text"][:max_len]
    except Exception:
        return result_json[:max_len]
    return None


class BusinessMonitorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BusinessMonitorRepository(db)

    async def record_upload(self, task_id: int, owner_id: int, http_latency_ms: float | None, image_size_bytes: int):
        await self.repo.upsert_upload_metric(task_id, owner_id, http_latency_ms, image_size_bytes)

    async def record_inference_complete(
        self,
        task_id: int,
        owner_id: int | None,
        inference_ms: float | None,
        avg_confidence: float | None,
        image_width: int | None,
        image_height: int | None,
    ):
        await self.repo.update_inference_metric(
            task_id,
            owner_id,
            inference_ms,
            avg_confidence,
            image_width,
            image_height,
        )

    async def log_error(
        self,
        error_type: str,
        message: str,
        detail: str | None,
        task_id: int | None,
        user_id: int | None,
    ):
        await self.repo.add_error_log(error_type, message, detail, task_id, user_id)

    async def build_stats(self, owner_id: int) -> dict:
        hourly_raw = await self.repo.hourly_inference_avg_24h(owner_id)
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        buckets = [now - timedelta(hours=i) for i in range(23, -1, -1)]
        by_label = {r["hour"]: r for r in hourly_raw}
        latency_24h = []
        for b in buckets:
            label = b.strftime("%m-%d %H:00")
            if label in by_label:
                latency_24h.append(by_label[label])
            else:
                latency_24h.append({"hour": label, "avg_inference_ms": 0.0, "count": 0})

        low_ids = await self.repo.low_confidence_task_ids(owner_id, limit=50)
        sc = await self.repo.status_counts_24h(owner_id)
        c = sc["counts"]
        pie = {
            "success": c.get("COMPLETED", 0),
            "failed": c.get("FAILED", 0),
            "in_progress": c.get("PENDING", 0) + c.get("PROCESSING", 0),
            "total": sc["total"],
        }
        return {
            "latency_24h": latency_24h,
            "low_confidence_task_ids": low_ids,
            "pie": pie,
        }

    async def list_bad_cases(self, owner_id: int) -> list[dict]:
        tasks = await self.repo.list_bad_case_tasks(owner_id, limit=30)
        items = []
        for t in tasks:
            items.append(
                {
                    "task_id": t.id,
                    "filename": t.filename,
                    "status": t.status.value,
                    "avg_confidence": float(t.avg_confidence) if t.avg_confidence is not None else None,
                    "inference_ms": float(t.inference_ms) if t.inference_ms is not None else None,
                    "file_url": storage_provider.get_file_url(t.file_path),
                    "created_at": t.created_at,
                    "result_preview": _result_text_preview(t.result),
                }
            )
        return items


async def daily_export_ocr_results_json() -> str | None:
    from app.core.database import AsyncSessionLocal

    os.makedirs(settings.OCR_RESULTS_JSON_BACKUP_DIR, exist_ok=True)
    end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=1)
    fname = f"ocr_results_{start.strftime('%Y%m%d')}.json"
    out_path = os.path.join(settings.OCR_RESULTS_JSON_BACKUP_DIR, fname)

    async with AsyncSessionLocal() as session:
        stmt = (
            select(OCRTask)
            .where(
                OCRTask.status == TaskStatus.COMPLETED,
                OCRTask.completed_at.is_not(None),
                OCRTask.completed_at >= start,
                OCRTask.completed_at < end,
                OCRTask.result.is_not(None),
            )
            .order_by(OCRTask.id)
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        payload = []
        for t in tasks:
            try:
                parsed = json.loads(t.result) if t.result else None
            except json.JSONDecodeError:
                parsed = t.result
            payload.append(
                {
                    "task_id": t.id,
                    "owner_id": t.owner_id,
                    "filename": t.filename,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                    "inference_ms": t.inference_ms,
                    "avg_confidence": t.avg_confidence,
                    "result": parsed,
                }
            )
        Path(out_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Daily OCR JSON backup written: %s (%s tasks)", out_path, len(payload))
    return out_path
