from datetime import datetime, timezone
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session
from langgraph.graph import END, START, StateGraph

from app.models.analysis import AnalysisTask, AnalysisTaskStep
from app.models.user import User
from app.services.products import identify_product
from app.services.retrieval import build_evidence_pack


WORKFLOW_STEPS = ["product_identification", "evidence_pack", "quality_check", "report_stub"]


class AnalysisWorkflowState(TypedDict, total=False):
    task_id: int
    product_identification: dict[str, Any]
    evidence_pack: dict[str, Any]
    quality_check: dict[str, Any]
    report_stub: dict[str, Any]


def create_analysis_task(db: Session, payload, user: User) -> AnalysisTask:
    task = AnalysisTask(
        task_type=payload.task_type,
        product_id=payload.product_id,
        product_name_input=payload.product_name,
        product_model_input=payload.product_model,
        target_industry_id=payload.target_industry_id,
        competitor_ids=payload.competitor_ids,
        user_question=payload.user_question,
        analysis_goals=payload.analysis_goals,
        output_format=payload.output_format,
        status="created",
        created_by=user.id,
    )
    db.add(task)
    db.flush()
    for step in WORKFLOW_STEPS:
        db.add(AnalysisTaskStep(task_id=task.id, step_name=step, status="pending"))
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: int) -> AnalysisTask | None:
    return db.scalar(select(AnalysisTask).where(AnalysisTask.id == task_id))


def list_task_steps(db: Session, task_id: int) -> list[AnalysisTaskStep]:
    return list(db.scalars(select(AnalysisTaskStep).where(AnalysisTaskStep.task_id == task_id)).all())


def _run_step(db: Session, task: AnalysisTask, step_name: str, input_json: dict, fn):
    step = db.scalar(
        select(AnalysisTaskStep).where(
            AnalysisTaskStep.task_id == task.id, AnalysisTaskStep.step_name == step_name
        )
    )
    if step is None:
        step = AnalysisTaskStep(task_id=task.id, step_name=step_name)
        db.add(step)
        db.flush()
    step.status = "running"
    step.input_json = input_json
    step.output_json = {}
    step.error_message = None
    step.started_at = datetime.now(timezone.utc)
    task.status = "running"
    task.current_step = step_name
    db.commit()
    try:
        result = fn()
        step.status = "completed"
        step.output_json = result or {}
        step.finished_at = datetime.now(timezone.utc)
        db.commit()
        return result
    except Exception as exc:  # noqa: BLE001
        step.status = "failed"
        step.error_message = str(exc)
        step.finished_at = datetime.now(timezone.utc)
        task.status = "failed"
        db.commit()
        raise


def _build_analysis_graph(db: Session, task: AnalysisTask):
    def product_identification_node(state: AnalysisWorkflowState) -> dict:
        if task.product_id:
            result = _run_step(
                db,
                task,
                "product_identification",
                {"product_id": task.product_id, "source": "provided"},
                lambda: {"product_id": task.product_id, "match_type": "provided"},
            )
            return {"product_identification": result}

        def identify() -> dict:
            matched, candidates, missing = identify_product(
                db,
                query=task.product_name_input or task.user_question or "",
                product_name=task.product_name_input,
                product_model=task.product_model_input,
                create_if_missing=True,
            )
            task.product_id = matched.id if matched else None
            return {
                "product_id": task.product_id,
                "candidates": [
                    {
                        "id": product.id,
                        "name": product.name,
                        "model": product.model,
                        "confidence": score,
                        "match_type": match_type,
                    }
                    for product, score, match_type in candidates
                ],
                "missing_information": missing,
            }

        result = _run_step(
            db,
            task,
            "product_identification",
            {
                "product_name_input": task.product_name_input,
                "product_model_input": task.product_model_input,
                "user_question": task.user_question,
            },
            identify,
        )
        return {"product_identification": result}

    def evidence_pack_node(state: AnalysisWorkflowState) -> dict:
        query = task.user_question or task.product_name_input or "产品分析"

        def evidence() -> dict:
            items, debug, missing = build_evidence_pack(
                db,
                query=query,
                task_id=task.id,
                product_id=task.product_id,
                target_industry_id=task.target_industry_id,
                competitor_ids=task.competitor_ids,
                top_k=16,
            )
            return {
                "evidence_count": len(items),
                "debug": debug,
                "missing_information": missing,
                "citations": [item.citation_code for item in items],
            }

        result = _run_step(
            db,
            task,
            "evidence_pack",
            {
                "query": query,
                "product_id": task.product_id,
                "target_industry_id": task.target_industry_id,
                "competitor_ids": task.competitor_ids,
            },
            evidence,
        )
        return {"evidence_pack": result}

    def quality_check_node(state: AnalysisWorkflowState) -> dict:
        evidence_result = state.get("evidence_pack", {})
        missing = evidence_result.get("missing_information", [])

        def quality() -> dict:
            status = "warning" if missing else "passed"
            return {"status": status, "checks": {"missing_information": missing, "citation_required": True}}

        result = _run_step(db, task, "quality_check", {"evidence_pack": evidence_result}, quality)
        return {"quality_check": result}

    def report_stub_node(state: AnalysisWorkflowState) -> dict:
        evidence_result = state.get("evidence_pack", {})
        quality_result = state.get("quality_check", {})

        def report_stub() -> dict:
            return {
                "facts": [],
                "analysis": [],
                "assumptions": [],
                "recommendations": [],
                "missing_information": quality_result.get("checks", {}).get("missing_information", []),
                "citations": evidence_result.get("citations", []),
                "summary": "已完成产品识别、证据包生成和质量检查。市场/竞品/销售策略报告将在后续周期扩展。",
            }

        result = _run_step(
            db,
            task,
            "report_stub",
            {"evidence_pack": evidence_result, "quality_check": quality_result},
            report_stub,
        )
        return {"report_stub": result}

    graph = StateGraph(AnalysisWorkflowState)
    graph.add_node("product_identification", product_identification_node)
    graph.add_node("evidence_pack", evidence_pack_node)
    graph.add_node("quality_check", quality_check_node)
    graph.add_node("report_stub", report_stub_node)
    graph.add_edge(START, "product_identification")
    graph.add_edge("product_identification", "evidence_pack")
    graph.add_edge("evidence_pack", "quality_check")
    graph.add_edge("quality_check", "report_stub")
    graph.add_edge("report_stub", END)
    return graph.compile(name="saleshelper_analysis_workflow")


def run_analysis_task(db: Session, task_id: int) -> AnalysisTask:
    task = db.get(AnalysisTask, task_id)
    if task is None:
        raise ValueError("analysis task not found")

    compiled_graph = _build_analysis_graph(db, task)
    result_state = compiled_graph.invoke({"task_id": task.id})
    task.status = "completed"
    task.current_step = "completed"
    task.result_json = {
        "engine": "langgraph",
        "product_identification": result_state.get("product_identification", {}),
        "evidence_pack": result_state.get("evidence_pack", {}),
        "quality_check": result_state.get("quality_check", {}),
        "report_stub": result_state.get("report_stub", {}),
    }
    db.commit()
    db.refresh(task)
    return task
