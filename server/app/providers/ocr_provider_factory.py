from typing import Protocol, Dict, Any

from app.core.config import settings
from app.providers.baidu_provider import baidu_provider
from app.providers.local_ocr_provider import local_ocr_provider


class OCRProvider(Protocol):
    async def ocr_general_basic(self, image_bytes: bytes) -> Dict[str, Any]:
        ...


def get_ocr_provider() -> OCRProvider:
    provider = settings.OCR_PROVIDER.lower().strip()
    if provider == "baidu":
        return baidu_provider
    return local_ocr_provider
