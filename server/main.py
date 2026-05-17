from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from app.controllers import ocr_controller, auth_controller, monitoring_controller, business_monitor_controller
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.app_logging import setup_app_logging
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
import logging
import time
import traceback

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.business_monitor_service import daily_export_ocr_results_json

_scheduler: AsyncIOScheduler | None = None

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    setup_app_logging()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        pass
    _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    _scheduler.add_job(
        daily_export_ocr_results_json,
        "cron",
        hour=0,
        minute=0,
        id="daily_ocr_json_backup",
        replace_existing=True,
    )
    _scheduler.start()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


app = FastAPI(title="OCR System API", lifespan=lifespan)
_RATE_BUCKET: dict[str, list[float]] = {}
_RATE_LIMIT = 120
_RATE_WINDOW_SECONDS = 60

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ocr_controller.router)
app.include_router(auth_controller.router)
app.include_router(monitoring_controller.router)
app.include_router(business_monitor_controller.router)


@app.middleware("http")
async def ocr_business_monitor_middleware(request: Request, call_next):
    from app.middleware.ocr_monitor_middleware import ocr_monitor_set_start

    return await ocr_monitor_set_start(request, call_next)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        await _try_log_monitoring(
            request,
            "WARNING",
            "api",
            f"HTTP {exc.status_code}: {exc.detail}",
            path=str(request.url.path),
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    await _try_log_monitoring(
        request,
        "ERROR",
        "api",
        str(exc) or type(exc).__name__,
        detail=tb[:8000],
        path=str(request.url.path),
    )
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


async def _try_log_monitoring(
    request: Request,
    level: str,
    source: str,
    message: str,
    detail: str | None = None,
    path: str | None = None,
    user_id: int | None = None,
):
    try:
        from app.services.monitoring_service import MonitoringService

        async with AsyncSessionLocal() as db:
            svc = MonitoringService(db)
            from app.models.monitoring import LogLevel

            lvl_map = {
                "ERROR": LogLevel.ERROR,
                "WARNING": LogLevel.WARNING,
                "INFO": LogLevel.INFO,
            }
            lvl = lvl_map.get(level, LogLevel.WARNING)
            await svc.log(lvl, source, message, detail=detail, path=path, user_id=user_id)
    except Exception as e:
        logger.warning("monitoring log failed: %s", e)


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if elapsed_ms > 8000:
        await _try_log_monitoring(
            request,
            "WARNING",
            "api",
            f"{request.method} {request.url.path} -> {response.status_code} ({elapsed_ms:.0f}ms)",
            path=str(request.url.path),
        )
    return response


@app.middleware("http")
async def global_rate_limit_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _RATE_BUCKET.setdefault(ip, [])
    cutoff = now - _RATE_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= _RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please retry later."},
        )
    bucket.append(now)
    return await call_next(request)

@app.get("/")
def read_root():
    return {"message": "OCR System API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
