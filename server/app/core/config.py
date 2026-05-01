import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "ocr_user"
    POSTGRES_PASSWORD: str = "ocr_password"
    POSTGRES_DB: str = "ocr_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def SYNC_DATABASE_URL(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minio_admin"
    MINIO_ROOT_PASSWORD: str = "minio_password"
    MINIO_BUCKET_NAME: str = "ocr-tasks"
    MINIO_SECURE: bool = False

    @property
    def MINIO_ACCESS_KEY(self):
        return self.MINIO_ROOT_USER

    @property
    def MINIO_SECRET_KEY(self):
        return self.MINIO_ROOT_PASSWORD

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"

    # AI Studio PaddleOCR API
    OCR_PROVIDER: str = "local"  # local | baidu
    OCR_API_URL: str = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
    OCR_ACCESS_TOKEN: str = ""
    OCR_MODEL: str = "PaddleOCR-VL-1.5"

    # Local OCR Models
    USE_LOCAL_MODELS: bool = False  # Set to True to use your own trained models
    DET_MODEL_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app", "inference_models", "det_db_resnet50_cbam")
    REC_MODEL_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app", "inference_models", "crnn_ctc_rare")

    # Security
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"

    @property
    def REDIS_URL(self):
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()
