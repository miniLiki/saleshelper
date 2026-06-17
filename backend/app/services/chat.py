from sqlalchemy.orm import Session

from app.models.analysis import Conversation, Message
from app.models.user import User
from app.services.ai_client import chat_text
from app.services.retrieval import build_evidence_pack


def answer_question(
    db: Session,
    user: User,
    question: str,
    conversation_id: int | None = None,
    task_id: int | None = None,
    filters: dict | None = None,
) -> tuple[Conversation, Message, str, list[dict], dict]:
    filters = filters or {}
    conversation = db.get(Conversation, conversation_id) if conversation_id else None
    if conversation is None:
        conversation = Conversation(title=question[:80] or "辅助问答", user_id=user.id, task_id=task_id)
        db.add(conversation)
        db.flush()
    user_message = Message(conversation_id=conversation.id, role="user", content=question)
    db.add(user_message)
    db.flush()
    evidence, debug, missing = build_evidence_pack(
        db,
        query=question,
        task_id=task_id,
        product_id=filters.get("product_id"),
        target_industry_id=filters.get("industry_id"),
        competitor_ids=filters.get("competitor_ids", []),
        top_k=8,
        persist=False,
    )
    citations = [
        {
            "citation_code": item.citation_code,
            "document_id": item.document_id,
            "chunk_id": item.chunk_id,
            "quote": item.quote,
            "score": item.score,
            "trust_level": item.trust_level,
            "metadata": item.metadata_json,
        }
        for item in evidence
    ]
    evidence_text = "\n\n".join(f"[{item.citation_code}] {item.content}" for item in evidence)
    fallback = (
        "事实：\n"
        + ("\n".join(f"- [{item.citation_code}] {item.quote}" for item in evidence[:4]) or "- 暂无资料支持。")
        + "\n\n分析：当前回答仅基于已召回证据，证据不足的结论不会确定化。\n"
        + "\n推测：暂无需要脱离证据的推测。\n"
        + "\n建议：请补充产品、行业、竞品或客户案例资料后再生成更完整判断。\n"
        + ("\n资料缺口：\n" + "\n".join(f"- {item}" for item in missing) if missing else "")
    )
    answer = chat_text(
        "你是公司内部产品分析、市场定位和销售辅助系统中的问答节点。只能基于给定证据回答，区分事实、分析、推测、建议和资料缺口，关键结论必须引用证据编号。",
        f"问题：{question}\n\n证据：\n{evidence_text}\n\n请用中文回答。",
        fallback,
    )
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        citations_json=citations,
        retrieval_debug_json={"debug": debug, "missing_information": missing},
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    return conversation, assistant_message, answer, citations, {"debug": debug, "missing_information": missing}
