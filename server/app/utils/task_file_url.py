from __future__ import annotations

from fastapi import Request

from app.core.security import create_file_view_token
from app.models.task import OCRTask
from app.providers.storage_provider import storage_provider


def build_task_file_url(
    task: OCRTask,
    request: Request | None = None,
    api_base: str | None = None,
) -> str | None:
    """优先返回经 API 代理的图片地址，局域网下不依赖 MinIO 的 localhost。"""
    if not task.file_path:
        return None

    base: str | None = None
    if request is not None:
        base = str(request.base_url).rstrip("/")
    elif api_base:
        base = api_base.rstrip("/")

    if base and task.owner_id is not None:
        token = create_file_view_token(task.id, task.owner_id)
        return f"{base}/ocr/task/{task.id}/file?token={token}"

    return storage_provider.get_file_url(task.file_path)
