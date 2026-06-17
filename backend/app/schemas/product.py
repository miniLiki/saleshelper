from pydantic import BaseModel


class ProductRead(BaseModel):
    id: int
    name: str
    model: str | None = None
    category: str | None = None
    description: str | None = None
    status: str
    confidence_level: float

    model_config = {"from_attributes": True}


class ProductIdentifyRequest(BaseModel):
    query: str
    product_name: str | None = None
    product_model: str | None = None
    create_if_missing: bool = False


class ProductCandidate(BaseModel):
    product: ProductRead
    confidence: float
    match_type: str


class ProductIdentifyResponse(BaseModel):
    matched_product: ProductRead | None
    candidates: list[ProductCandidate]
    missing_information: list[str] = []
