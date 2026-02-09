from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any
from models.task import TaskStatus

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
    file_url: Optional[str] = None

    class Config:
        from_attributes = True
