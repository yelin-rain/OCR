"""
业务感知监控：为 /ocr 路由记录请求起始时间，供控制器写入 HTTP 延迟等指标。
avg_confidence、推理耗时在异步 Worker 完成后写入 ocr_run_metrics。
"""

import time

from starlette.requests import Request


async def ocr_monitor_set_start(request: Request, call_next):
    path = request.url.path or ""
    if path.startswith("/ocr"):
        request.state.ocr_mon_started = time.perf_counter()
    return await call_next(request)
