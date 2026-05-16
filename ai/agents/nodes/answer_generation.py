"""
ai/agents/nodes/answer_generation.py
──────────────────────────────────────
Node 6 — Answer Generation (NLG).

Chuyển kết quả SQL thành câu trả lời tiếng Việt tự nhiên.

Cải tiến so với phiên bản cũ:
- Chain LangChain thuần — không raw httpx
- Fallback template gọn hơn, tách biệt với chain logic
- Xử lý trường hợp execution_success=False rõ ràng hơn

LangGraph node contract:
    Input : GraphState  (đọc "user_question", "rows", "execution_success", "execution_error")
    Output: dict        (trả về {"answer": ...})
"""

from __future__ import annotations

import json
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ai.agents.state import GraphState
from ai.agents.llm_client import get_llm_creative

logger = logging.getLogger(__name__)

# ── Prompt ────────────────────────────────────────────────────────────────────
_SYSTEM = """\
Bạn là trợ lý trả lời câu hỏi về cơ sở dữ liệu sinh viên.

Nhiệm vụ: Dựa vào câu hỏi gốc và kết quả truy vấn SQL, viết câu trả lời:
- Bằng tiếng Việt, tự nhiên và thân thiện
- Trình bày dữ liệu rõ ràng (dùng danh sách đánh số nếu nhiều kết quả)
- Nếu kết quả rỗng: nói rõ không tìm thấy dữ liệu phù hợp
- KHÔNG đề cập đến SQL hay database trong câu trả lời
- Độ dài vừa phải (2-6 dòng)
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", (
        "Câu hỏi: {user_question}\n\n"
        "Kết quả truy vấn ({row_count} dòng, hiển thị tối đa 20):\n{rows_json}"
    )),
])


def _fallback_answer(user_question: str, rows: list[dict]) -> str:
    """Template đơn giản khi không có LLM."""
    if not rows:
        return f"Không tìm thấy dữ liệu phù hợp với câu hỏi: {user_question}"
    if len(rows) == 1:
        parts = [f"{k}: {v}" for k, v in rows[0].items()]
        return "Kết quả: " + ", ".join(parts)
    lines = [f"Tìm thấy {len(rows)} kết quả:"]
    for i, row in enumerate(rows[:10], 1):
        parts = [f"{k}: {v}" for k, v in row.items()]
        lines.append(f"{i}. {', '.join(parts)}")
    if len(rows) > 10:
        lines.append(f"... và {len(rows) - 10} kết quả khác.")
    return "\n".join(lines)


def answer_generation_node(state: GraphState) -> dict:
    """LangGraph node: sinh câu trả lời tự nhiên."""
    user_question = state.get("user_question", "")
    rows = state.get("rows", [])
    success = state.get("execution_success", False)
    error_msg = state.get("execution_error")

    # Nếu execution thất bại → trả thông báo lỗi thân thiện
    if not success:
        answer = (
            f"Xin lỗi, tôi không thể trả lời câu hỏi '{user_question}' lúc này. "
            f"Lỗi kỹ thuật: {error_msg or 'Không xác định'}."
        )
        return {"answer": answer}

    # Giới hạn rows gửi vào LLM
    rows_for_prompt = rows[:20]
    rows_json = json.dumps(rows_for_prompt, ensure_ascii=False, indent=2)

    try:
        llm = get_llm_creative()
        chain = _prompt | llm | StrOutputParser()
        answer = chain.invoke({
            "user_question": user_question,
            "row_count": len(rows),
            "rows_json": rows_json,
        })
        answer = answer.strip()
        logger.info("[Answer] %s", answer[:80])
        return {"answer": answer}
    except Exception as exc:
        logger.warning("[Answer] LLM thất bại: %s — dùng fallback.", exc)
        return {"answer": _fallback_answer(user_question, rows)}