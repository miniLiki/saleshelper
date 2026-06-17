from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.models.knowledge import ExtractionCandidate
from app.models.user import User
from app.schemas.document import ExtractionCandidateListResponse, IngestionJobListResponse
from app.services.auth import require_permission
from app.services.documents import list_ingestion_jobs
from app.services.extraction import apply_candidate_to_knowledge
from app.services.indexing import rebuild_milvus, rebuild_neo4j, rebuild_pg_embeddings, verify_external_indexes

router = APIRouter()


@router.get("/ingestion-jobs", response_model=IngestionJobListResponse)
def read_ingestion_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:read")),
) -> IngestionJobListResponse:
    items, total = list_ingestion_jobs(db, page=page, page_size=page_size)
    return IngestionJobListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/extraction-candidates", response_model=ExtractionCandidateListResponse)
def read_extraction_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    candidate_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:read")),
) -> ExtractionCandidateListResponse:
    statement = select(ExtractionCandidate)
    if status:
        statement = statement.where(ExtractionCandidate.status == status)
    if candidate_type:
        statement = statement.where(ExtractionCandidate.candidate_type == candidate_type)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = db.scalars(
        statement.order_by(ExtractionCandidate.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ExtractionCandidateListResponse(items=list(items), total=total, page=page, page_size=page_size)


@router.post("/extraction-candidates/{candidate_id}/confirm")
def confirm_extraction_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:read")),
) -> dict:
    candidate = db.get(ExtractionCandidate, candidate_id)
    if candidate is None:
        raise AppError(404, "候选知识不存在")
    apply_candidate_to_knowledge(db, candidate)
    candidate.status = "confirmed"
    candidate.reviewed_by = current_user.id
    db.commit()
    return {"status": "confirmed", "candidate_id": candidate_id}


@router.post("/extraction-candidates/{candidate_id}/ignore")
def ignore_extraction_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:read")),
) -> dict:
    candidate = db.get(ExtractionCandidate, candidate_id)
    if candidate is None:
        raise AppError(404, "候选知识不存在")
    candidate.status = "ignored"
    candidate.reviewed_by = current_user.id
    db.commit()
    return {"status": "ignored", "candidate_id": candidate_id}


@router.post("/indexes/rebuild")
def rebuild_indexes(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:read")),
) -> dict:
    embeddings = rebuild_pg_embeddings(db)
    return {"embeddings": embeddings, "milvus": rebuild_milvus(db), "neo4j": rebuild_neo4j(db)}


@router.get("/indexes/verify")
def verify_indexes(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:read")),
) -> dict:
    return verify_external_indexes(db)
