from celery_worker import celery_app
from app.services.ocr_service import OCRService
import asyncio

@celery_app.task(bind=True)
def process_ocr_task(self, task_id: int, use_local_models: bool | None = None):
    """
    Celery task to run OCR on a file.
    Delegates logic to OCRService.
    """
    print(f"Processing task {task_id} (use_local_models={use_local_models})")
    asyncio.run(OCRService.process_task_logic(task_id, use_local_models=use_local_models))
    return {"task_id": task_id, "status": "COMPLETED"}
