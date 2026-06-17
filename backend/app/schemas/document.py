from datetime import datetime

from pydantic import BaseModel, Field


class DocumentRead(BaseModel):
    id: int
    title: str
    file_name: str
    file_type: str
    business_type: str
    source_type: str
    product_id: str | None
    competitor_id: str | None
    industry_id: str | None
    trust_level: int
    permission_scope: str
    version: int
    storage_path: str
    status: str
    uploaded_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentRead]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class DocumentVersionRead(BaseModel):
    id: int
    version: int
    file_name: str
    storage_path: str
    file_size: int
    checksum: str
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestionJobRead(BaseModel):
    id: int
    document_id: int | None
    version_id: int | None
    job_type: str
    status: str
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkRead(BaseModel):
    id: int
    document_id: int
    version_id: int | None
    chunk_index: int
    title_path: str
    content: str
    page_number: int | None
    sheet_name: str | None
    token_count: int
    metadata_json: dict
    vector_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentRead):
    versions: list[DocumentVersionRead]
    ingestion_jobs: list[IngestionJobRead]
    chunks: list[DocumentChunkRead] = []


class IngestionJobListResponse(BaseModel):
    items: list[IngestionJobRead]
    total: int
    page: int
    page_size: int


class ExtractionCandidateRead(BaseModel):
    id: int
    candidate_type: str
    payload_json: dict
    source_chunk_id: int | None
    document_id: int | None
    confidence: float
    extraction_version: str
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExtractionCandidateListResponse(BaseModel):
    items: list[ExtractionCandidateRead]
    total: int
    page: int
    page_size: int
