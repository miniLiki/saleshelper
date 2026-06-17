from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.knowledge import Product
from app.models.user import User
from app.schemas.product import ProductCandidate, ProductIdentifyRequest, ProductIdentifyResponse, ProductRead
from app.services.auth import require_permission
from app.services.products import identify_product

router = APIRouter()


@router.get("", response_model=list[ProductRead])
def list_products(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:read")),
) -> list[ProductRead]:
    return list(db.scalars(select(Product).order_by(Product.updated_at.desc()).limit(200)).all())


@router.post("/identify", response_model=ProductIdentifyResponse)
def identify_product_endpoint(
    payload: ProductIdentifyRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:read")),
) -> ProductIdentifyResponse:
    matched, candidates, missing = identify_product(
        db,
        query=payload.query,
        product_name=payload.product_name,
        product_model=payload.product_model,
        create_if_missing=payload.create_if_missing,
    )
    return ProductIdentifyResponse(
        matched_product=matched,
        candidates=[
            ProductCandidate(product=product, confidence=confidence, match_type=match_type)
            for product, confidence, match_type in candidates
        ],
        missing_information=missing,
    )
