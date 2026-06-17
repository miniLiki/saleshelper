from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.retrieval import EvidencePackRequest, EvidencePackResponse, EvidenceRead
from app.services.auth import require_permission
from app.services.graph import query_graph
from app.services.retrieval import build_evidence_pack

router = APIRouter()


@router.post("/evidence-pack", response_model=EvidencePackResponse)
def evidence_pack(
    payload: EvidencePackRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:read")),
) -> EvidencePackResponse:
    items, debug, missing = build_evidence_pack(
        db,
        query=payload.query,
        task_id=payload.task_id,
        product_id=payload.product_id,
        target_industry_id=payload.target_industry_id,
        competitor_ids=payload.competitor_ids,
        top_k=payload.top_k,
        persist=payload.task_id is not None,
    )
    return EvidencePackResponse(
        query=payload.query,
        items=[
            EvidenceRead(
                id=item.id,
                citation_code=item.citation_code,
                group_name=item.group_name,
                source_type=item.source_type,
                document_id=item.document_id,
                chunk_id=item.chunk_id,
                content=item.content,
                quote=item.quote,
                score=item.score,
                trust_level=item.trust_level,
                metadata_json=item.metadata_json,
            )
            for item in items
        ],
        missing_information=missing,
        debug=debug,
    )


@router.get("/graph-query")
def graph_query(
    question_type: str,
    name: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:read")),
) -> dict:
    return query_graph(db, question_type=question_type, name=name)
