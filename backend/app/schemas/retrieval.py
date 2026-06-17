from pydantic import BaseModel, Field


class EvidencePackRequest(BaseModel):
    query: str
    task_id: int | None = None
    product_id: int | None = None
    target_industry_id: int | None = None
    competitor_ids: list[int] = Field(default_factory=list)
    top_k: int = 12


class EvidenceRead(BaseModel):
    id: int | None = None
    citation_code: str
    group_name: str
    source_type: str
    document_id: int | None
    chunk_id: int | None
    content: str
    quote: str | None
    score: float
    trust_level: int
    metadata_json: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class EvidencePackResponse(BaseModel):
    query: str
    items: list[EvidenceRead]
    missing_information: list[str] = []
    debug: dict = Field(default_factory=dict)
