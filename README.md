# OCR Text Recognition Platform

A foundational OCR system built with React, FastAPI, Celery, and PaddleOCR.

## Architecture

- **Frontend**: React (Vite) + TypeScript + TailwindCSS
- **Backend**: FastAPI (Python)
- **Task Queue**: Celery + Redis
- **Storage**: MinIO (S3 Compatible)
- **Database**: PostgreSQL
- **OCR Engine**: PaddleOCR

## Prerequisites

- Docker & Docker Compose
- Python 3.9+
- Node.js 18+

## Quick Start

### 1. Start Infrastructure

Run the following command to start Redis, PostgreSQL, and MinIO:

```bash
docker-compose up -d
```

Access MinIO Console at `http://localhost:9001` (User: `minio_admin`, Password: `minio_password`).

### 2. Setup Backend

Navigate to the `server` directory:

```bash
cd server
```

Install dependencies (recommend using a virtual environment):

```bash
pip install -r requirements.txt
# Note: You may need to install system dependencies for PaddleOCR (e.g., libgomp1)
```

### 2. 启动后端 (Backend)

建议使用 **Python 3.11** (或 3.10-3.12)，暂不支持 Python 3.13+。

```bash
cd server
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
pip install greenlet  # 必须安装，用于处理异步 ORM

# 启动 API 服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

在**另一个终端** (同样需要 activate 虚拟环境) 启动任务队列消费者：

```bash
cd server
source .venv/Scripts/activate
# Windows 开发环境（推荐）
# 使用 solo 池避免多进程在 Windows 上的权限问题
.venv/Scripts/celery.exe -A celery_worker.celery_app worker --loglevel=info -P solo --concurrency 1

# Linux/macOS
celery -A celery_worker.celery_app worker --loglevel=info
```

_注意：修改代码后，API 和 Celery 两个终端都需要重启才能生效。_

#### 可选：严格模式启动检查

- 若希望后端在启动阶段强校验数据库/MinIO依赖，请在代码中移除启动容错逻辑（lifespan 中的 try/except 以及存储初始化中的 try/except）。此模式更严格，适合部署环境；当前默认容错更适合本地开发。

### 3. 启动前端 (Frontend)

```bash
cd frontend
npm install
npm run dev
```

### 4. 使用数据库 (Database)

```bash
docker compose exec db psql -U ocr_user -d ocr_db -c "ALTER USER ocr_user WITH PASSWORD '12345678';"
\dt
```

## 功能使用

- **多模式上传**：点击方框选择文件，或直接将图片拖拽到界面中。
- **实时进度**：任务状态会自动更新 (Pending -> Processing -> Completed/Failed)。
- **停止任务**：对于正在处理中的任务，将鼠标悬停在任务列表项上，会出现红色的“停止”按钮。
- **查看结果**：点击任务可查看原图及 OCR 识别出的文字和置信度。
