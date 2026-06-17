from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document, DocumentChunk, IngestionJob
from app.services.extraction import extract_document_chunks
from app.services.indexing import embed_chunks, rebuild_knowledge_relations, rebuild_milvus, rebuild_neo4j
from app.services.parsers import parse_document_bytes, split_into_chunks
from app.storage.minio_client import ObjectStorage


def _job(db: Session, document_id: int, job_type: str) -> IngestionJob:
    job = IngestionJob(
        document_id=document_id,
        job_type=job_type,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _finish_job(db: Session, job: IngestionJob, status: str, error_message: str | None = None, metadata: dict | None = None) -> None:
    job.status = status
    job.error_message = error_message
    job.metadata_json = metadata or {}
    job.finished_at = datetime.now(timezone.utc)
    db.commit()


def parse_document(db: Session, document_id: int, storage: ObjectStorage | None = None) -> dict:
    document = db.get(Document, document_id)
    if document is None:
        raise ValueError("document not found")
    running_job = db.scalar(
        select(IngestionJob).where(
            IngestionJob.document_id == document_id,
            IngestionJob.job_type.in_(["parse", "extract", "index"]),
            IngestionJob.status == "running",
        )
    )
    if running_job is not None:
        raise ValueError("document is already being processed")
    job = _job(db, document_id, "parse")
    try:
        data = (storage or ObjectStorage()).get_bytes(document.storage_path)
        blocks = parse_document_bytes(data, document.file_name, document.file_type)
        chunks = split_into_chunks(blocks)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        version_id = document.versions[-1].id if document.versions else None
        created: list[DocumentChunk] = []
        for index, chunk in enumerate(chunks):
            row = DocumentChunk(
                document_id=document.id,
                version_id=version_id,
                chunk_index=index,
                title_path=chunk.title_path,
                content=chunk.content,
                page_number=chunk.page_number,
                sheet_name=chunk.sheet_name,
                token_count=max(1, len(chunk.content) // 2),
                metadata_json={
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                    "business_type": document.business_type,
                    "source_type": document.source_type,
                    "trust_level": document.trust_level,
                    "product_id": document.product_id,
                    "competitor_id": document.competitor_id,
                    "industry_id": document.industry_id,
                },
            )
            db.add(row)
            created.append(row)
        document.status = "parsed"
        db.commit()
        _finish_job(db, job, "completed", metadata={"chunks": len(created)})
        return {"document_id": document_id, "chunks": len(created)}
    except Exception as exc:  # noqa: BLE001
        document.status = "parse_failed"
        _finish_job(db, job, "failed", str(exc))
        raise


def process_document(db: Session, document_id: int, storage: ObjectStorage | None = None) -> dict:
    parse_result = parse_document(db, document_id, storage=storage)
    document = db.get(Document, document_id)
    if document is None:
        raise ValueError("document not found")
    extract_job = _job(db, document_id, "extract")
    try:
        candidates = extract_document_chunks(db, document)
        _finish_job(db, extract_job, "completed", metadata={"candidates": len(candidates)})
    except Exception as exc:  # noqa: BLE001
        _finish_job(db, extract_job, "failed", str(exc))
        raise

    index_job = _job(db, document_id, "index")
    try:
        chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document_id)).all()
        embed_chunks(db, chunks)
        relations = rebuild_knowledge_relations(db)
        milvus = rebuild_milvus(db)
        neo4j = rebuild_neo4j(db)
        if settings.enable_milvus and milvus.get("status") != "ok":
            raise RuntimeError(f"Milvus index rebuild failed: {milvus}")
        if settings.enable_neo4j and neo4j.get("status") != "ok":
            raise RuntimeError(f"Neo4j graph rebuild failed: {neo4j}")
        document.status = "indexed"
        db.commit()
        _finish_job(
            db,
            index_job,
            "completed",
            metadata={"chunks": len(chunks), "relations": relations, "milvus": milvus, "neo4j": neo4j},
        )
        return {**parse_result, "candidates": len(candidates), "chunks_indexed": len(chunks), "milvus": milvus, "neo4j": neo4j}
    except Exception as exc:  # noqa: BLE001
        document.status = "index_failed"
        _finish_job(db, index_job, "failed", str(exc))
        raise
