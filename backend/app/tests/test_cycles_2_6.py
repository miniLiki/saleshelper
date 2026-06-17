from app.models.analysis import AnalysisTask, Conversation
from app.models.document import Document, DocumentVersion
from app.models.knowledge import ExtractionCandidate, Product, ProductParameter, SellingPoint
from app.models.user import User
from app.services.analysis_workflow import create_analysis_task, run_analysis_task
from app.services.chat import answer_question
from app.services.ingestion import process_document
from app.services.retrieval import build_evidence_pack


class BytesStorage:
    def __init__(self, data: bytes):
        self.data = data

    def get_bytes(self, object_name: str) -> bytes:
        return self.data


def _seed_document(db_session):
    document = Document(
        title="XX-100 产品资料",
        file_name="xx-100.txt",
        file_type="txt",
        business_type="product_material",
        source_type="internal_product_doc",
        product_id="XX-100",
        trust_level=5,
        permission_scope="internal",
        storage_path="documents/xx-100.txt",
        status="uploaded",
    )
    db_session.add(document)
    db_session.flush()
    version = DocumentVersion(
        document_id=document.id,
        version=1,
        file_name=document.file_name,
        storage_path=document.storage_path,
        file_size=128,
        checksum="test",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(document)
    return document


def test_process_document_extracts_chunks_and_knowledge(db_session):
    document = _seed_document(db_session)
    data = "产品：XX-100\n型号：XX-100\n行业：制造业\n优势：部署快，维护简单\n吞吐量：1000件/小时".encode()

    result = process_document(db_session, document.id, storage=BytesStorage(data))

    assert result["chunks"] >= 1
    assert db_session.query(ExtractionCandidate).count() >= 1
    product = db_session.query(Product).filter(Product.name == "XX-100").one()
    assert db_session.query(ProductParameter).filter(ProductParameter.product_id == product.id).count() >= 1
    assert db_session.query(SellingPoint).filter(SellingPoint.product_id == product.id).count() >= 1


def test_evidence_pack_analysis_task_and_chat(db_session):
    document = _seed_document(db_session)
    data = "产品：XX-100\n行业：制造业\n优势：部署快，维护简单\n吞吐量：1000件/小时".encode()
    process_document(db_session, document.id, storage=BytesStorage(data))

    evidence, debug, missing = build_evidence_pack(db_session, query="XX-100 适合制造业吗", top_k=5)
    assert evidence
    assert debug["selected"] >= 1

    class Payload:
        task_type = "full_product_analysis"
        product_name = "XX-100"
        product_model = None
        product_id = None
        target_industry_id = None
        competitor_ids = []
        user_question = "XX-100 适合制造业吗"
        analysis_goals = ["evidence_pack", "report_stub"]
        output_format = "structured_report"

    user = db_session.query(User).filter_by(username="admin").one()
    task = create_analysis_task(db_session, Payload, user)
    task = run_analysis_task(db_session, task.id)
    assert task.status == "completed"
    assert task.result_json["engine"] == "langgraph"

    conversation, message, answer, citations, retrieval_debug = answer_question(
        db_session, user, "XX-100 的优势是什么？"
    )
    assert isinstance(conversation, Conversation)
    assert answer
    assert citations
