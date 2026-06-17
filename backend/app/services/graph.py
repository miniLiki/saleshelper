from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import Industry, KnowledgeRelation, Product, SellingPoint


def query_graph(db: Session, question_type: str, name: str | None = None) -> dict:
    if question_type == "industry_products":
        industry = db.scalar(select(Industry).where(Industry.name.contains(name or "")))
        if industry is None:
            return {"items": [], "missing_information": ["未找到行业节点"]}
        relations = db.scalars(
            select(KnowledgeRelation).where(
                KnowledgeRelation.relation_type == "APPLIES_TO",
                KnowledgeRelation.target_type == "Industry",
                KnowledgeRelation.target_id == industry.id,
            )
        ).all()
        products = [
            db.get(Product, relation.source_id)
            for relation in relations
            if relation.source_type == "Product"
        ]
        return {
            "industry": industry.name,
            "items": [
                {"id": product.id, "name": product.name, "model": product.model}
                for product in products
                if product is not None
            ],
            "missing_information": [] if products else ["暂无产品与该行业的图谱关系"],
        }
    if question_type == "product_selling_points":
        product = db.scalar(select(Product).where(Product.name.contains(name or "")))
        if product is None:
            return {"items": [], "missing_information": ["未找到产品节点"]}
        relations = db.scalars(
            select(KnowledgeRelation).where(
                KnowledgeRelation.relation_type == "HAS_SELLING_POINT",
                KnowledgeRelation.source_type == "Product",
                KnowledgeRelation.source_id == product.id,
            )
        ).all()
        points = [
            db.get(SellingPoint, relation.target_id)
            for relation in relations
            if relation.target_type == "SellingPoint"
        ]
        return {
            "product": product.name,
            "items": [
                {"id": point.id, "title": point.title, "description": point.description}
                for point in points
                if point is not None
            ],
            "missing_information": [] if points else ["暂无产品卖点图谱关系"],
        }
    return {"items": [], "missing_information": ["未知图谱查询类型"]}
