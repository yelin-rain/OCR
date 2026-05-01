from fastapi import FastAPI, Request
from app.controllers import ocr_controller, auth_controller
from app.core.database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        pass
    yield

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
