from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.core.database import Base


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)
    error_type = Column(String(64), index=True, nullable=False)
    message = Column(Text, nullable=False)
    detail = Column(Text, nullable=True)
    task_id = Column(
        Integer, ForeignKey("ocr_tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class OCRRunMetric(Base):
    """业务监控：与 OCR 任务 1:1，记录 HTTP 与推理侧指标。"""

    __tablename__ = "ocr_run_metrics"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(
        Integer,
        ForeignKey("ocr_tasks.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    http_latency_ms = Column(Float, nullable=True)
    image_size_bytes = Column(Integer, nullable=True)
    inference_ms = Column(Float, nullable=True)
    avg_confidence = Column(Float, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
