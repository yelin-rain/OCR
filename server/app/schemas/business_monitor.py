from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HourlyLatencyPoint(BaseModel):
    hour: str
    avg_inference_ms: float
    count: int


class PieStats(BaseModel):
    success: int = Field(description="已完成")
    failed: int = Field(description="失败")
    in_progress: int = Field(description="排队或处理中")
    total: int


class MonitorStatsResponse(BaseModel):
    latency_24h: list[HourlyLatencyPoint] = Field(description="近24小时按小时平均推理耗时")
    low_confidence_task_ids: list[int] = Field(description="置信度低于80%的任务ID（滚动预警）")
    pie: PieStats


class BadCaseItem(BaseModel):
    task_id: int
    filename: str
    status: str
    avg_confidence: Optional[float] = None
    inference_ms: Optional[float] = None
    file_url: Optional[str] = None
    created_at: datetime
    result_preview: Optional[str] = Field(None, description="识别文本摘要")


class BadCasesResponse(BaseModel):
    items: list[BadCaseItem]
