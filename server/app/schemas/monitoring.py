from datetime import datetime

from pydantic import BaseModel, Field


class SystemLogEntry(BaseModel):
    id: int
    level: str
    source: str
    message: str
    detail: str | None = None
    path: str | None = None
    user_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BackupRecordEntry(BaseModel):
    id: int
    filename: str
    file_path: str
    size_bytes: int
    success: bool
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MonitoringSummary(BaseModel):
    errors_last_24h: int = Field(description="ERROR 级别日志条数（近 24 小时）")
    warnings_last_24h: int
    total_logs_last_24h: int
    last_backup_at: datetime | None = None
    last_backup_ok: bool | None = None
    backup_dir: str
    app_log_file: str


class BackupTriggerResponse(BaseModel):
    success: bool
    message: str
    record: BackupRecordEntry | None = None
