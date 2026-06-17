from datetime import datetime

from pydantic import BaseModel, Field


class AnalysisTaskCreate(BaseModel):
    task_type: str = "full_product_analysis"
    product_name: str | None = None
    product_model: str | None = None
    product_id: int | None = None
    target_industry_id: int | None = None
    competitor_ids: list[int] = Field(default_factory=list)
    user_question: str | None = None
    analysis_goals: list[str] = Field(default_factory=lambda: ["evidence_pack", "report_stub"])
    output_format: str = "structured_report"


class AnalysisTaskStepRead(BaseModel):
    id: int
    task_id: int
    step_name: str
    status: str
    input_json: dict
    output_json: dict
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class AnalysisTaskRead(BaseModel):
    id: int
    task_type: str
    product_id: int | None
    product_name_input: str | None
    product_model_input: str | None
    target_industry_id: int | None
    competitor_ids: list[int]
    user_question: str | None
    analysis_goals: list[str]
    output_format: str
    status: str
    current_step: str | None
    result_json: dict
    created_at: datetime
    updated_at: datetime
    steps: list[AnalysisTaskStepRead] = []

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    task_id: int | None = None
    question: str
    filters: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    citations: list[dict] = Field(default_factory=list)
    retrieval_debug: dict = Field(default_factory=dict)
