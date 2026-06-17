from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_type: Mapped[str] = mapped_column(String(80), default="full_product_analysis", index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    product_name_input: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_model_input: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_industry_id: Mapped[int | None] = mapped_column(ForeignKey("industries.id"), nullable=True)
    competitor_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    user_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    output_format: Mapped[str] = mapped_column(String(80), default="structured_report")
    status: Mapped[str] = mapped_column(String(40), default="created", index=True)
    current_step: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AnalysisTaskStep(Base):
    __tablename__ = "analysis_task_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("analysis_tasks.id"), index=True)
    step_name: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("analysis_tasks.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True, index=True)
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    competitor_id: Mapped[int | None] = mapped_column(ForeignKey("competitors.id"), nullable=True)
    industry_id: Mapped[int | None] = mapped_column(ForeignKey("industries.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    trust_level: Mapped[int] = mapped_column(Integer, default=3)
    group_name: Mapped[str] = mapped_column(String(80), default="general", index=True)
    citation_code: Mapped[str] = mapped_column(String(40), default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="辅助问答")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("analysis_tasks.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(40), index=True)
    content: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    retrieval_debug_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"), nullable=True, index=True)
    evidence_item_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_items.id"), nullable=True)
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id"), nullable=True)
    citation_code: Mapped[str] = mapped_column(String(40), default="")
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
