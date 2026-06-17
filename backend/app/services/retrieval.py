from collections import defaultdict

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.analysis import EvidenceItem
from app.models.document import Document, DocumentChunk
from app.models.knowledge import KnowledgeRelation, Product
from app.services.ai_client import embed_text
from app.services.indexing import cosine_similarity, search_milvus


GROUP_BY_BUSINESS_TYPE = {
    "product_material": "product_facts",
    "industry_material": "industry_materials",
    "customer_case": "customer_cases",
    "competitor_material": "competitor_materials",
    "sales_faq": "sales_materials",
}


def _keyword_score(query: str, text: str) -> float:
    terms = [term for term in query.lower().split() if term]
    if not terms:
        return 0.0
    lowered = text.lower()
    hits = sum(1 for term in terms if term in lowered)
    return hits / len(terms)


def build_evidence_pack(
    db: Session,
    query: str,
    task_id: int | None = None,
    product_id: int | None = None,
    target_industry_id: int | None = None,
    competitor_ids: list[int] | None = None,
    top_k: int = 12,
    persist: bool = True,
) -> tuple[list[EvidenceItem], dict, list[str]]:
    competitor_ids = competitor_ids or []
    query_embedding = embed_text(query)
    product = db.get(Product, product_id) if product_id else None
    product_refs = {
        value
        for value in [
            str(product_id) if product_id else None,
            product.name if product else None,
            product.model if product else None,
        ]
        if value
    }
    statement = select(DocumentChunk, Document).join(Document, Document.id == DocumentChunk.document_id)
    if target_industry_id:
        statement = statement.where(or_(Document.industry_id == str(target_industry_id), Document.industry_id.is_(None)))
    rows = db.execute(statement).all()
    milvus_result = search_milvus(query_embedding, top_k=max(top_k * 2, 20))
    milvus_scores = {
        int(item["chunk_id"]): float(item.get("score") or 0.0)
        for item in milvus_result.get("items", [])
        if item.get("chunk_id") is not None
    }
    graph_chunk_ids: set[int] = set()
    if product_id:
        graph_chunk_ids.update(
            relation.source_chunk_id
            for relation in db.scalars(
                select(KnowledgeRelation).where(
                    KnowledgeRelation.source_type == "Product",
                    KnowledgeRelation.source_id == product_id,
                    KnowledgeRelation.source_chunk_id.is_not(None),
                )
            ).all()
            if relation.source_chunk_id is not None
        )

    scored: list[tuple[float, DocumentChunk, Document, dict]] = []
    for chunk, document in rows:
        semantic = cosine_similarity(chunk.embedding, query_embedding)
        keyword = _keyword_score(query, chunk.content + " " + document.title + " " + document.file_name)
        milvus = milvus_scores.get(chunk.id, 0.0)
        graph = 1.0 if chunk.id in graph_chunk_ids else 0.0
        trust = document.trust_level / 5
        score = semantic * 0.36 + keyword * 0.24 + milvus * 0.20 + graph * 0.08 + trust * 0.12
        if product_refs and (
            document.product_id in product_refs
            or any(ref.lower() in chunk.content.lower() for ref in product_refs)
        ):
            score += 0.08
        if competitor_ids and document.competitor_id in {str(value) for value in competitor_ids}:
            score += 0.08
        if score > 0:
            scored.append(
                (
                    score,
                    chunk,
                    document,
                    {"semantic": semantic, "keyword": keyword, "milvus": milvus, "graph": graph, "trust": trust},
                )
            )

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = scored[:top_k]
    if persist and task_id is not None:
        db.query(EvidenceItem).filter(EvidenceItem.task_id == task_id).delete()

    items: list[EvidenceItem] = []
    groups = defaultdict(int)
    for index, (score, chunk, document, debug) in enumerate(selected, start=1):
        group_name = GROUP_BY_BUSINESS_TYPE.get(document.business_type, "general")
        groups[group_name] += 1
        item = EvidenceItem(
            task_id=task_id,
            source_type="document_chunk",
            document_id=document.id,
            chunk_id=chunk.id,
            content=chunk.content,
            quote=chunk.content[:260],
            score=round(float(score), 4),
            trust_level=document.trust_level,
            group_name=group_name,
            citation_code=f"E{index}",
            metadata_json={
                "document_title": document.title,
                "file_name": document.file_name,
                "page_number": chunk.page_number,
                "sheet_name": chunk.sheet_name,
                "title_path": chunk.title_path,
                **debug,
            },
        )
        if persist:
            db.add(item)
        items.append(item)
    if persist:
        db.commit()
        for item in items:
            db.refresh(item)
    missing = []
    for expected in ["product_facts", "industry_materials", "customer_cases", "competitor_materials", "sales_materials"]:
        if groups[expected] == 0:
            missing.append(f"缺少 {expected} 相关证据")
    return items, {
        "candidates": len(scored),
        "selected": len(items),
        "groups": dict(groups),
        "retrievers": {
            "postgres_chunks": len(rows),
            "milvus": {"status": milvus_result.get("status"), "hits": len(milvus_scores), "error": milvus_result.get("error")},
            "graph_chunk_hints": len(graph_chunk_ids),
        },
    }, missing
