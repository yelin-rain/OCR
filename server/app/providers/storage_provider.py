from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import io
from urllib.parse import urlparse, urlunparse

class StorageProvider:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        if not self.client.bucket_exists(settings.MINIO_BUCKET_NAME):
            self.client.make_bucket(settings.MINIO_BUCKET_NAME)

    def upload_file(self, file_data: bytes, filename: str, content_type: str) -> str:
        """Uploads a file to MinIO and returns the object name."""
        try:
            result = self.client.put_object(
                settings.MINIO_BUCKET_NAME,
                filename,
                io.BytesIO(file_data),
                len(file_data),
                content_type=content_type
            )
            return filename
        except S3Error as e:
            print(f"MinIO Upload Error: {e}")
            raise e

    def get_file_url(self, filename: str) -> str:
        """Generate a presigned URL for the file."""
        url = self.client.get_presigned_url(
            "GET",
            settings.MINIO_BUCKET_NAME,
            filename,
        )
        return self._rewrite_public_host(url)

    def _rewrite_public_host(self, url: str) -> str:
        public_host = settings.MINIO_PUBLIC_HOST
        if not public_host:
            return url
        parsed = urlparse(url)
        scheme = "https" if settings.MINIO_SECURE else "http"
        if "://" not in public_host:
            netloc = public_host
        else:
            public_parsed = urlparse(
                public_host if "://" in public_host else f"//{public_host}"
            )
            scheme = public_parsed.scheme or scheme
            netloc = public_parsed.netloc or public_parsed.path
        return urlunparse((scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

    def download_file(self, filename: str) -> bytes:
        """Download file content as bytes."""
        try:
            response = self.client.get_object(settings.MINIO_BUCKET_NAME, filename)
            return response.read()
        except S3Error as e:
            print(f"MinIO Download Error: {e}")
            raise e
        finally:
            if 'response' in locals():
                response.close()

    def delete_file(self, filename: str):
        """Delete a file from MinIO."""
        try:
            self.client.remove_object(settings.MINIO_BUCKET_NAME, filename)
        except S3Error as e:
            print(f"MinIO Delete Error: {e}")
            raise e
                
storage_provider = StorageProvider()
