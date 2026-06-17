from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import DocumentDetail, DocumentListResponse, DocumentRead
from app.services.auth import require_permission
from app.services.documents import create_document, get_document_detail, list_documents
from app.services.ingestion import parse_document, process_document

router = APIRouter()


@router.post("", response_model=DocumentRead)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    file_type: str = Form(...),
    business_type: str = Form(...),
    source_type: str = Form(...),
    trust_level: int = Form(3, ge=1, le=5),
    permission_scope: str = Form("internal"),
    product_id: str | None = Form(None),
    competitor_id: str | None = Form(None),
    industry_id: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents:write")),
) -> DocumentRead:
    try:
        return await create_document(
            db=db,
            current_user=current_user,
            file=file,
            title=title,
            file_type=file_type,
            business_type=business_type,
            source_type=source_type,
            trust_level=trust_level,
            permission_scope=permission_scope,
            product_id=product_id,
            competitor_id=competitor_id,
            industry_id=industry_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise AppError(502, f"资料上传失败：{exc}") from exc


@router.get("", response_model=DocumentListResponse)
def read_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    file_type: str | None = None,
    business_type: str | None = None,
    source_type: str | None = None,
    product_id: str | None = None,
    competitor_id: str | None = None,
    industry_id: str | None = None,
    trust_level: int | None = Query(None, ge=1, le=5),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:read")),
) -> DocumentListResponse:
    items, total = list_documents(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        file_type=file_type,
        business_type=business_type,
        source_type=source_type,
        product_id=product_id,
        competitor_id=competitor_id,
        industry_id=industry_id,
        trust_level=trust_level,
    )
    return DocumentListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentDetail)
def read_document_detail(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:read")),
) -> DocumentDetail:
    document = get_document_detail(db, document_id)
    if document is None:
        raise AppError(404, "资料不存在")
    return document


@router.post("/{document_id}/parse")
def parse_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:write")),
) -> dict:
    try:
        return parse_document(db, document_id)
    except Exception as exc:  # noqa: BLE001
        raise AppError(500, f"解析失败：{exc}") from exc


@router.post("/{document_id}/process")
def process_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("documents:write")),
) -> dict:
    try:
        return process_document(db, document_id)
    except Exception as exc:  # noqa: BLE001
        raise AppError(500, f"处理失败：{exc}") from exc
