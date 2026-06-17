from difflib import SequenceMatcher

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.knowledge import Product, ProductAlias


def identify_product(
    db: Session,
    query: str,
    product_name: str | None = None,
    product_model: str | None = None,
    create_if_missing: bool = False,
) -> tuple[Product | None, list[tuple[Product, float, str]], list[str]]:
    search_text = (product_name or query or "").strip()
    candidates: list[tuple[Product, float, str]] = []
    products = db.scalars(select(Product)).all()
    for product in products:
        names = [product.name, product.model or ""]
        aliases = db.scalars(select(ProductAlias).where(ProductAlias.product_id == product.id)).all()
        names.extend(alias.alias for alias in aliases)
        best = 0.0
        match_type = "fuzzy"
        for name in names:
            if not name:
                continue
            if search_text == name or product_model == product.model:
                best = max(best, 1.0)
                match_type = "exact"
            elif search_text and search_text in name or name in search_text:
                best = max(best, 0.86)
                match_type = "alias_or_contains"
            else:
                best = max(best, SequenceMatcher(None, search_text.lower(), name.lower()).ratio())
        if best >= 0.35:
            candidates.append((product, round(best, 4), match_type))
    candidates.sort(key=lambda item: item[1], reverse=True)
    matched = candidates[0][0] if candidates and candidates[0][1] >= 0.75 else None
    missing: list[str] = []
    if matched is None and create_if_missing and search_text:
        matched = Product(
            name=search_text,
            model=product_model,
            status="temporary",
            confidence_level=0.4,
            description="用户输入创建的临时产品对象",
        )
        db.add(matched)
        db.commit()
        db.refresh(matched)
        candidates.insert(0, (matched, 0.4, "temporary"))
    elif matched is None:
        missing.append("未找到高置信度产品，请补充产品资料或选择候选产品")
    return matched, candidates[:8], missing
