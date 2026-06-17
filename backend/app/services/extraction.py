import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.knowledge import (
    Competitor,
    CompetitorProduct,
    CustomerCase,
    ExtractionCandidate,
    Industry,
    Product,
    ProductParameter,
    SalesMaterial,
    SellingPoint,
)
from app.services.ai_client import chat_json


@dataclass
class ExtractedItem:
    candidate_type: str
    payload: dict[str, Any]
    confidence: float = 0.55


def _uniq(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = value.strip(" ：:，,。；;")
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def heuristic_extract(chunk: DocumentChunk, document: Document) -> list[ExtractedItem]:
    text = chunk.content
    items: list[ExtractedItem] = []
    product_names = _uniq(re.findall(r"(?:产品|型号|名称)[:：]\s*([A-Za-z0-9_\-\u4e00-\u9fff]{2,40})", text))
    for name in product_names[:3]:
        items.append(
            ExtractedItem(
                "product",
                {"name": name, "model": document.product_id or None, "description": text[:220]},
                0.62,
            )
        )
    param_matches = re.findall(r"([A-Za-z0-9_\-\u4e00-\u9fff]{2,30})[:：]\s*([^\n|；;]{1,80})", text)
    for name, value in param_matches[:12]:
        if name not in {"产品", "型号", "名称", "客户", "行业"}:
            items.append(
                ExtractedItem("product_parameter", {"parameter_name": name, "parameter_value": value}, 0.58)
            )
    selling_points = _uniq(re.findall(r"(?:优势|卖点|特点)[:：]\s*([^\n。；;]{4,120})", text))
    for point in selling_points[:6]:
        items.append(ExtractedItem("selling_point", {"title": point[:80], "description": point}, 0.58))
    industries = _uniq(re.findall(r"(?:行业|适用行业)[:：]\s*([^\n。；;]{2,80})", text))
    for name in industries[:6]:
        items.append(ExtractedItem("industry", {"name": name}, 0.55))
    competitors = _uniq(re.findall(r"(?:竞品|竞争对手|友商)[:：]\s*([^\n。；;]{2,80})", text))
    for name in competitors[:5]:
        items.append(ExtractedItem("competitor", {"name": name}, 0.56))
    if document.business_type == "customer_case":
        customer = re.search(r"(?:客户|公司)[:：]\s*([^\n。；;]{2,80})", text)
        items.append(
            ExtractedItem(
                "customer_case",
                {
                    "customer_name": customer.group(1) if customer else document.title,
                    "solution_summary": text[:260],
                    "implementation_result": "",
                },
                0.55,
            )
        )
    if document.business_type == "sales_faq":
        items.append(
            ExtractedItem(
                "sales_material",
                {"title": document.title, "material_type": "faq", "content_summary": text[:260]},
                0.6,
            )
        )
    return items


def llm_extract(chunk: DocumentChunk, document: Document) -> list[ExtractedItem]:
    fallback = {"items": [item.__dict__ for item in heuristic_extract(chunk, document)]}
    payload = chat_json(
        "你是结构化知识抽取节点，只能输出 JSON。字段必须来自原文，不确定则少抽取。",
        f"""
资料类型：{document.business_type}
标题：{document.title}
文本：
{chunk.content[:3500]}

输出 JSON:
{{"items":[{{"candidate_type":"product|product_parameter|selling_point|industry|competitor|competitor_product|customer_case|sales_material","payload":{{}}, "confidence":0.0}}]}}
""",
        fallback,
    )
    items: list[ExtractedItem] = []
    for raw in payload.get("items", []):
        candidate_type = raw.get("candidate_type") or raw.get("type")
        item_payload = raw.get("payload") or {}
        if candidate_type and isinstance(item_payload, dict):
            items.append(
                ExtractedItem(candidate_type, item_payload, float(raw.get("confidence", 0.55)))
            )
    return items


def _get_or_create_industry(db: Session, name: str) -> Industry:
    industry = db.scalar(select(Industry).where(Industry.name == name))
    if industry is None:
        industry = Industry(name=name)
        db.add(industry)
        db.flush()
    return industry


def _get_or_create_product(db: Session, payload: dict[str, Any], chunk_id: int | None) -> Product | None:
    name = payload.get("name") or payload.get("product_name")
    if not name:
        return None
    model = payload.get("model") or payload.get("product_model")
    product = db.scalar(select(Product).where(Product.name == name, Product.model == model))
    if product is None:
        product = Product(
            name=name,
            model=model,
            category=payload.get("category"),
            description=payload.get("description"),
            confidence_level=float(payload.get("confidence", 0.6)),
            source_chunk_id=chunk_id,
        )
        db.add(product)
        db.flush()
    elif not product.verified_by_user:
        product.description = product.description or payload.get("description")
    return product


def _infer_product(db: Session, payload: dict[str, Any], chunk_id: int | None, document: Document | None = None) -> Product | None:
    product_name = payload.get("product_name") or payload.get("product") or payload.get("name")
    product_model = payload.get("product_model") or payload.get("model")
    document_product_ref = document.product_id if document else None
    identifiers = [value for value in [product_name, product_model, document_product_ref] if value]
    for identifier in identifiers:
        product = db.scalar(
            select(Product).where(
                (Product.name == identifier) | (Product.model == identifier)
            )
        )
        if product is not None:
            return product
    if chunk_id is not None:
        product = db.scalar(select(Product).where(Product.source_chunk_id == chunk_id))
        if product is not None:
            return product
    if document_product_ref:
        return _get_or_create_product(
            db,
            {"name": str(document_product_ref), "model": product_model},
            chunk_id,
        )
    return None


def apply_candidate_to_knowledge(
    db: Session,
    candidate: ExtractionCandidate,
    document: Document | None = None,
) -> None:
    payload = candidate.payload_json or {}
    chunk_id = candidate.source_chunk_id
    if candidate.candidate_type == "product":
        _get_or_create_product(db, payload, chunk_id)
    elif candidate.candidate_type == "product_parameter":
        product = _infer_product(db, payload, chunk_id, document)
        db.add(
            ProductParameter(
                product_id=product.id if product else None,
                parameter_name=payload.get("parameter_name") or payload.get("name") or "未命名参数",
                parameter_value=str(payload.get("parameter_value") or payload.get("value") or ""),
                unit=payload.get("unit"),
                source_chunk_id=chunk_id,
                confidence=candidate.confidence,
            )
        )
    elif candidate.candidate_type == "selling_point":
        product = _infer_product(db, payload, chunk_id, document)
        db.add(
            SellingPoint(
                product_id=product.id if product else None,
                title=payload.get("title") or payload.get("name") or "未命名卖点",
                description=payload.get("description"),
                source_chunk_id=chunk_id,
                confidence=candidate.confidence,
            )
        )
    elif candidate.candidate_type == "industry" and payload.get("name"):
        _get_or_create_industry(db, payload["name"])
    elif candidate.candidate_type == "competitor" and payload.get("name"):
        competitor = db.scalar(select(Competitor).where(Competitor.name == payload["name"]))
        if competitor is None:
            db.add(Competitor(name=payload["name"], description=payload.get("description"), source_chunk_id=chunk_id))
    elif candidate.candidate_type == "competitor_product":
        db.add(
            CompetitorProduct(
                name=payload.get("name") or "未命名竞品产品",
                model=payload.get("model"),
                strengths=payload.get("strengths"),
                weaknesses=payload.get("weaknesses"),
                source_chunk_id=chunk_id,
            )
        )
    elif candidate.candidate_type == "customer_case":
        industry = _get_or_create_industry(db, payload["industry"]) if payload.get("industry") else None
        db.add(
            CustomerCase(
                customer_name=payload.get("customer_name") or "未命名客户",
                customer_industry_id=industry.id if industry else None,
                solution_summary=payload.get("solution_summary"),
                implementation_result=payload.get("implementation_result"),
                source_chunk_id=chunk_id,
            )
        )
    elif candidate.candidate_type == "sales_material":
        db.add(
            SalesMaterial(
                title=payload.get("title") or "销售材料",
                material_type=payload.get("material_type") or "faq",
                content_summary=payload.get("content_summary"),
                source_chunk_id=chunk_id,
            )
        )


def extract_document_chunks(db: Session, document: Document) -> list[ExtractionCandidate]:
    candidates: list[ExtractionCandidate] = []
    chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document.id)).all()
    for chunk in chunks:
        for item in llm_extract(chunk, document):
            candidate = ExtractionCandidate(
                candidate_type=item.candidate_type,
                payload_json=item.payload,
                source_chunk_id=chunk.id,
                document_id=document.id,
                confidence=item.confidence,
                status="pending",
            )
            db.add(candidate)
            db.flush()
            if candidate.confidence >= 0.55:
                apply_candidate_to_knowledge(db, candidate, document=document)
            candidates.append(candidate)
    db.commit()
    return candidates
