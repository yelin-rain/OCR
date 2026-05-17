import logging
import os
from logging.handlers import RotatingFileHandler

from app.core.config import settings


def setup_app_logging() -> None:
    os.makedirs(settings.APP_LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    has_file_handler = any(
        isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == os.path.abspath(settings.APP_LOG_FILE)
        for h in root.handlers
    )
    if not has_file_handler:
        fh = RotatingFileHandler(
            settings.APP_LOG_FILE,
            maxBytes=2 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        fh.setLevel(logging.INFO)
        root.addHandler(fh)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(logging.WARNING)
        root.addHandler(sh)


def get_uvicorn_log_config() -> dict:
    """供 uvicorn 使用，与文件日志目录一致。"""
    os.makedirs(settings.APP_LOG_DIR, exist_ok=True)
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": settings.APP_LOG_FILE,
                "maxBytes": 2097152,
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "root": {"level": "INFO", "handlers": ["file"]},
    }
