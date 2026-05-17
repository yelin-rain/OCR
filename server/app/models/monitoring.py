from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class LogLevel(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), index=True, nullable=False)
    source = Column(String(64), index=True, nullable=False)
    message = Column(Text, nullable=False)
    detail = Column(Text, nullable=True)
    path = Column(String(512), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", backref="system_logs")


class DataBackupRecord(Base):
    __tablename__ = "data_backup_records"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
