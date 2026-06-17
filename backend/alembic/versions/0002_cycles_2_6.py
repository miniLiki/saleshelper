"""cycles 2 to 6 knowledge, retrieval, and analysis schema

Revision ID: 0002_cycles_2_6
Revises: 0001_initial
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_cycles_2_6"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _create_table_if_missing(name: str, *columns, **kwargs) -> None:
    if name not in _tables():
        op.create_table(name, *columns, **kwargs)


def _create_index_if_missing(name: str, table: str, columns: list[str], unique: bool = False) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}
    if name not in indexes:
        op.create_index(name, table, columns, unique=unique)


def upgrade() -> None:
    _create_table_if_missing(
        "document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("version_id", sa.Integer(), sa.ForeignKey("document_versions.id"), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("title_path", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("sheet_name", sa.String(length=255), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("vector_status", sa.String(length=40), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ["id", "document_id", "chunk_index", "vector_status"]:
        _create_index_if_missing(f"ix_document_chunks_{column}", "document_chunks", [column])

    _create_table_if_missing(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("confidence_level", sa.Float(), nullable=False),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("verified_by_user", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("name", "model", name="uq_products_name_model"),
    )
    for column in ["id", "name", "model", "status"]:
        _create_index_if_missing(f"ix_products_{column}", "products", [column])

    _create_table_if_missing(
        "product_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_product_aliases_product_id", "product_aliases", ["product_id"])
    _create_index_if_missing("ix_product_aliases_alias", "product_aliases", ["alias"])

    _create_table_if_missing(
        "product_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_product_models_product_id", "product_models", ["product_id"])
    _create_index_if_missing("ix_product_models_model_name", "product_models", ["model_name"])

    _create_table_if_missing(
        "industries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_industries_name", "industries", ["name"], unique=True)

    _create_table_if_missing(
        "scenarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("industry_id", sa.Integer(), sa.ForeignKey("industries.id"), nullable=True),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_scenarios_name", "scenarios", ["name"], unique=True)

    _create_table_if_missing(
        "pain_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("industry_id", sa.Integer(), sa.ForeignKey("industries.id"), nullable=True),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_pain_points_name", "pain_points", ["name"], unique=True)

    _create_table_if_missing(
        "product_parameters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("parameter_name", sa.String(length=255), nullable=False),
        sa.Column("parameter_value", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=True),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verified_by_user", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_product_parameters_product_id", "product_parameters", ["product_id"])
    _create_index_if_missing("ix_product_parameters_parameter_name", "product_parameters", ["parameter_name"])

    _create_table_if_missing(
        "selling_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verified_by_user", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_selling_points_product_id", "selling_points", ["product_id"])
    _create_index_if_missing("ix_selling_points_title", "selling_points", ["title"])

    _create_table_if_missing(
        "customer_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_industry_id", sa.Integer(), sa.ForeignKey("industries.id"), nullable=True),
        sa.Column("customer_size", sa.String(length=120), nullable=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("scenarios.id"), nullable=True),
        sa.Column("pain_point_id", sa.Integer(), sa.ForeignKey("pain_points.id"), nullable=True),
        sa.Column("solution_summary", sa.Text(), nullable=True),
        sa.Column("implementation_result", sa.Text(), nullable=True),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("trust_level", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_customer_cases_customer_name", "customer_cases", ["customer_name"])
    _create_index_if_missing("ix_customer_cases_product_id", "customer_cases", ["product_id"])

    _create_table_if_missing(
        "sales_materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("material_type", sa.String(length=80), nullable=False),
        sa.Column("content_summary", sa.Text(), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_sales_materials_title", "sales_materials", ["title"])

    _create_table_if_missing(
        "competitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_competitors_name", "competitors", ["name"], unique=True)

    _create_table_if_missing(
        "competitor_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("strengths", sa.Text(), nullable=True),
        sa.Column("weaknesses", sa.Text(), nullable=True),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_competitor_products_competitor_id", "competitor_products", ["competitor_id"])
    _create_index_if_missing("ix_competitor_products_name", "competitor_products", ["name"])

    _create_table_if_missing(
        "competitor_parameters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_product_id", sa.Integer(), sa.ForeignKey("competitor_products.id"), nullable=True),
        sa.Column("parameter_name", sa.String(length=255), nullable=False),
        sa.Column("parameter_value", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=True),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_competitor_parameters_competitor_product_id", "competitor_parameters", ["competitor_product_id"])
    _create_index_if_missing("ix_competitor_parameters_parameter_name", "competitor_parameters", ["parameter_name"])

    _create_table_if_missing(
        "knowledge_relations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ["source_type", "source_id", "relation_type", "target_type", "target_id"]:
        _create_index_if_missing(f"ix_knowledge_relations_{column}", "knowledge_relations", [column])

    _create_table_if_missing(
        "extraction_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_type", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("source_chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("extraction_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ["candidate_type", "source_chunk_id", "document_id", "status"]:
        _create_index_if_missing(f"ix_extraction_candidates_{column}", "extraction_candidates", [column])

    _create_table_if_missing(
        "analysis_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_type", sa.String(length=80), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("product_name_input", sa.String(length=255), nullable=True),
        sa.Column("product_model_input", sa.String(length=255), nullable=True),
        sa.Column("target_industry_id", sa.Integer(), sa.ForeignKey("industries.id"), nullable=True),
        sa.Column("competitor_ids", sa.JSON(), nullable=False),
        sa.Column("user_question", sa.Text(), nullable=True),
        sa.Column("analysis_goals", sa.JSON(), nullable=False),
        sa.Column("output_format", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("current_step", sa.String(length=120), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ["id", "task_type", "product_id", "status"]:
        _create_index_if_missing(f"ix_analysis_tasks_{column}", "analysis_tasks", [column])

    _create_table_if_missing(
        "analysis_task_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("analysis_tasks.id"), nullable=False),
        sa.Column("step_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    _create_index_if_missing("ix_analysis_task_steps_task_id", "analysis_task_steps", ["task_id"])
    _create_index_if_missing("ix_analysis_task_steps_step_name", "analysis_task_steps", ["step_name"])
    _create_index_if_missing("ix_analysis_task_steps_status", "analysis_task_steps", ["status"])

    _create_table_if_missing(
        "evidence_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("analysis_tasks.id"), nullable=True),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id"), nullable=True),
        sa.Column("industry_id", sa.Integer(), sa.ForeignKey("industries.id"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("trust_level", sa.Integer(), nullable=False),
        sa.Column("group_name", sa.String(length=80), nullable=False),
        sa.Column("citation_code", sa.String(length=40), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ["task_id", "source_type", "document_id", "chunk_id", "product_id", "group_name"]:
        _create_index_if_missing(f"ix_evidence_items_{column}", "evidence_items", [column])

    _create_table_if_missing(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("analysis_tasks.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    _create_table_if_missing(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False),
        sa.Column("retrieval_debug_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_messages_conversation_id", "messages", ["conversation_id"])
    _create_index_if_missing("ix_messages_role", "messages", ["role"])

    _create_table_if_missing(
        "citations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("evidence_item_id", sa.Integer(), sa.ForeignKey("evidence_items.id"), nullable=True),
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("document_chunks.id"), nullable=True),
        sa.Column("citation_code", sa.String(length=40), nullable=False),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index_if_missing("ix_citations_message_id", "citations", ["message_id"])


def downgrade() -> None:
    for table_name in [
        "citations",
        "messages",
        "conversations",
        "evidence_items",
        "analysis_task_steps",
        "analysis_tasks",
        "extraction_candidates",
        "knowledge_relations",
        "competitor_parameters",
        "competitor_products",
        "competitors",
        "sales_materials",
        "customer_cases",
        "selling_points",
        "product_parameters",
        "pain_points",
        "scenarios",
        "industries",
        "product_models",
        "product_aliases",
        "products",
        "document_chunks",
    ]:
        if table_name in _tables():
            op.drop_table(table_name)
