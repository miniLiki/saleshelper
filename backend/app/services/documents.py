import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document, DocumentVersion, IngestionJob
from app.models.user import User
from app.storage.minio_client import ObjectStorage


def create_failed_upload_job(db: Session, error_message: str) -> IngestionJob:
    job = IngestionJob(
        job_type="upload",
        status="failed",
        error_message=error_message,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


async def create_document(
    db: Session,
    current_user: User,
    file: UploadFile,
    title: str,
    file_type: str,
    business_type: str,
    source_type: str,
    trust_level: int,
    permission_scope: str,
    product_id: str | None = None,
    competitor_id: str | None = None,
    industry_id: str | None = None,
    storage: ObjectStorage | None = None,
) -> Document:
    data = await file.read()
    checksum = hashlib.sha256(data).hexdigest()
    object_name = f"documents/{uuid4()}-{file.filename}"
    started_at = datetime.now(timezone.utc)

    storage_client = storage or ObjectStorage()
    try:
        storage_client.put_bytes(object_name, data, file.content_type)
    except Exception as exc:  # noqa: BLE001 - preserve external storage error for task state.
        create_failed_upload_job(db, str(exc))
        raise

    document = Document(
        title=title,
        file_name=file.filename or title,
        file_type=file_type,
        business_type=business_type,
        source_type=source_type,
        product_id=product_id,
        competitor_id=competitor_id,
        industry_id=industry_id,
        trust_level=trust_level,
        permission_scope=permission_scope,
        storage_path=object_name,
        status="uploaded",
        uploaded_by=current_user.id,
    )
    db.add(document)
    db.flush()

    version = DocumentVersion(
        document_id=document.id,
        version=1,
        file_name=document.file_name,
        storage_path=object_name,
        file_size=len(data),
        checksum=checksum,
        created_by=current_user.id,
    )
    db.add(version)
    db.flush()

    job = IngestionJob(
        document_id=document.id,
        version_id=version.id,
        job_type="upload",
        status="completed",
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(document)
    try:
        from app.workers.celery_app import process_document_task

        process_document_task.delay(document.id)
    except Exception:
        # The API remains usable when Redis/Celery is not running; admins can retry from the console.
        pass
    return document


def list_documents(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    file_type: str | None = None,
    business_type: str | None = None,
    source_type: str | None = None,
    product_id: str | None = None,
    competitor_id: str | None = None,
    industry_id: str | None = None,
    trust_level: int | None = None,
) -> tuple[list[Document], int]:
    statement = select(Document)
    filters = {
        Document.status: status,
        Document.file_type: file_type,
        Document.business_type: business_type,
        Document.source_type: source_type,
        Document.product_id: product_id,
        Document.competitor_id: competitor_id,
        Document.industry_id: industry_id,
        Document.trust_level: trust_level,
    }
    for column, value in filters.items():
        if value not in (None, ""):
            statement = statement.where(column == value)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = db.scalars(
        statement.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(items), total


def get_document_detail(db: Session, document_id: int) -> Document | None:
    return db.scalar(
        select(Document)
        .options(
            selectinload(Document.versions),
            selectinload(Document.ingestion_jobs),
            selectinload(Document.chunks),
        )
        .where(Document.id == document_id)
    )


def list_ingestion_jobs(db: Session, page: int = 1, page_size: int = 20) -> tuple[list[IngestionJob], int]:
    statement = select(IngestionJob)
    total = db.scalar(select(func.count()).select_from(IngestionJob)) or 0
    items = db.scalars(
        statement.order_by(IngestionJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(items), total
