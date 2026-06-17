from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.models.analysis import AnalysisTask
from app.models.user import User
from app.schemas.analysis import AnalysisTaskCreate, AnalysisTaskRead, AnalysisTaskStepRead, ChatRequest, ChatResponse
from app.services.analysis_workflow import create_analysis_task, get_task, list_task_steps, run_analysis_task
from app.services.auth import get_current_user, require_permission
from app.services.chat import answer_question

router = APIRouter()


def _task_read(db: Session, task: AnalysisTask) -> AnalysisTaskRead:
    return AnalysisTaskRead.model_validate(task).model_copy(
        update={"steps": [AnalysisTaskStepRead.model_validate(step) for step in list_task_steps(db, task.id)]}
    )


@router.post("/analysis-tasks", response_model=AnalysisTaskRead)
def create_task(
    payload: AnalysisTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents:read")),
) -> AnalysisTaskRead:
    task = create_analysis_task(db, payload, current_user)
    return _task_read(db, task)


@router.get("/analysis-tasks", response_model=list[AnalysisTaskRead])
def list_tasks(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:read")),
) -> list[AnalysisTaskRead]:
    tasks = db.scalars(select(AnalysisTask).order_by(AnalysisTask.created_at.desc()).limit(100)).all()
    return [_task_read(db, task) for task in tasks]


@router.get("/analysis-tasks/{task_id}", response_model=AnalysisTaskRead)
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:read")),
) -> AnalysisTaskRead:
    task = get_task(db, task_id)
    if task is None:
        raise AppError(404, "分析任务不存在")
    return _task_read(db, task)


@router.post("/analysis-tasks/{task_id}/run", response_model=AnalysisTaskRead)
def run_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:read")),
) -> AnalysisTaskRead:
    try:
        task = run_analysis_task(db, task_id)
        return _task_read(db, task)
    except Exception as exc:  # noqa: BLE001
        raise AppError(500, f"任务运行失败：{exc}") from exc


@router.post("/analysis-tasks/{task_id}/retry", response_model=AnalysisTaskRead)
def retry_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:read")),
) -> AnalysisTaskRead:
    return run_task(task_id, db, _)


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    conversation, message, answer, citations, debug = answer_question(
        db,
        current_user,
        question=payload.question,
        conversation_id=payload.conversation_id,
        task_id=payload.task_id,
        filters=payload.filters,
    )
    return ChatResponse(
        conversation_id=conversation.id,
        message_id=message.id,
        answer=answer,
        citations=citations,
        retrieval_debug=debug,
    )
