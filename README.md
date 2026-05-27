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
npm run dev -- --host 0.0.0.0
```

### 4. 使用数据库 (Database)

```bash
docker compose exec db psql -U ocr_user -d ocr_db -c "ALTER USER ocr_user WITH PASSWORD '12345678';"
\dt
```

## 局域网访问（同 WiFi 演示）

让同一局域网内的同学通过浏览器使用本机服务：

1. **查本机 WLAN 的 IPv4**（不要用 WSL 的 `172.31.x.x`）：

   ```bash
   ipconfig
   ```

   使用 **WLAN** 网卡地址，例如 `10.114.212.23`。

2. **启动服务**（均需在本机运行）：
   - 基础设施：`docker compose up -d`（Redis / Postgres / MinIO）
   - 后端：`uvicorn main:app --host 0.0.0.0 --port 8000`
   - Celery：见上文 Windows 命令
   - 前端：`cd frontend && npm run dev`（已配置监听 `0.0.0.0`）

3. **发给对方的链接**：

   ```text
   http://<你的WLAN的IP>:5173
   ```

   例如 `http://10.114.212.23:5173`。

4. **API 地址**：前端会根据访问页面的 IP 自动请求 `http://<同一IP>:8000`，无需同学改 `localhost`。若需固定 API，可复制 `frontend/.env.lan.example` 为 `.env.local` 并设置 `VITE_API_BASE`。

5. **防火墙**：放行 **5173**（前端）、**8000**（API）即可；任务图片经 API 代理返回，一般**不必**对同学开放 MinIO 的 9000 端口。

6. **图片**：任务 `file_url` 会生成为 `http://<你的IP>:8000/ocr/task/{id}/file?token=...`，局域网内可直接显示。修改后端后需**重启 uvicorn**，并让同学**刷新页面**重新拉取任务列表。

7. **自检**：在本机浏览器用 **IP 地址**（不要用 `localhost`）打开上述链接，能注册登录后再让同学访问。

8. **校园网**：部分 WiFi 开启「客户端隔离」，设备之间无法互访；可改用手机热点测试。

## 本地自训练模型（det + rec）

`server/.env` 中保持：

```env
OCR_PROVIDER=local
USE_LOCAL_MODELS=True
```

识别模型目录：`server/app/inference_models/crnn_ctc_rare`（由 `rec_rare_2` 导出）  
检测模型目录：`server/app/inference_models/det_db_resnet50_cbam`（由 `db_resnet50_cbam` 导出）

重新导出识别模型（在 `server` 目录，Paddle 3.3 需 PIR 导出）：

```bash
cd modal/PaddleOCR
FLAGS_enable_pir_api=1 python tools/export_model.py \
  -c output/rec_rare_2/config.yml \
  -o Global.save_inference_dir=C:/ocr_export/rec_pir \
  Global.pretrained_model=output/rec_rare_2/best_accuracy \
  Global.use_gpu=False Global.export_with_pir=True
```

然后将 `inference.json`、`inference.pdiparams`、`inference.yml` 复制到 `crnn_ctc_rare/`。  
也可用：`python scripts/export_paddleocr_models.py export --skip-det ...`（见脚本注释）。

安装或更新模型后，**必须重启 API 与 Celery**，启动日志应出现 `local-det_db_resnet50_cbam+rec_rare_2`。

## 功能使用

- **多模式上传**：点击方框选择文件，或直接将图片拖拽到界面中。
- **实时进度**：任务状态会自动更新 (Pending -> Processing -> Completed/Failed)。
- **停止任务**：对于正在处理中的任务，将鼠标悬停在任务列表项上，会出现红色的“停止”按钮。
- **查看结果**：点击任务可查看原图及 OCR 识别出的文字和置信度。
