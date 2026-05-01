from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.task import TaskStatus

class TaskBase(BaseModel):
    filename: str

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: int
    status: TaskStatus
    owner_id: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[str] = None # JSON String
    correction_log: Optional[str] = None # JSON String
    model_version: Optional[str] = None
    inference_ms: Optional[float] = None
    avg_confidence: Optional[float] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    file_url: Optional[str] = None

    class Config:
        from_attributes = True


class TaskCorrectionItem(BaseModel):
    index: int
    original: str
    corrected: str


class TaskCorrectionRequest(BaseModel):
    corrections: list[TaskCorrectionItem]
