from celery import Celery

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.ingestion import process_document

celery_app = Celery(
    "saleshelper",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
)


@celery_app.task(name="documents.process")
def process_document_task(document_id: int) -> dict:
    with SessionLocal() as db:
        return process_document(db, document_id)
