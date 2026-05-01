from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.core.database import Base

# Enums
class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# Models
class OCRTask(Base):
    __tablename__ = "ocr_tasks"

    id = Column(Integer, primary_key=True, index=True)
    celery_task_id = Column(String, nullable=True)
    filename = Column(String, index=True)
    file_path = Column(String) # MinIO path
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    result = Column(Text, nullable=True) # JSON string of results
    correction_log = Column(Text, nullable=True) # JSON string: [{index, original, corrected, at}]
    model_version = Column(String, nullable=True)
    inference_ms = Column(Float, nullable=True)
    avg_confidence = Column(Float, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="ocr_tasks")

