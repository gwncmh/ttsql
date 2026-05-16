"""
ai/agents/nodes/rewriter.py
────────────────────────────
Node 1 — Query Rewriter.

Dùng LangChain PromptTemplate + LLM chain thay vì raw httpx.
Fallback về câu gốc nếu LLM không khả dụng.

LangGraph node contract:
    Input : GraphState  (đọc "user_question")
    Output: dict        (trả về {"rewritten_query": ...})
"""

from __future__ import annotations

import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ai.agents.state import GraphState
from ai.agents.llm_client import get_llm

logger = logging.getLogger(__name__)

# ── Prompt ────────────────────────────────────────────────────────────────────
_SYSTEM = """\
Bạn là chuyên gia chuẩn hóa câu hỏi cho hệ thống Text-to-SQL.

Nhiệm vụ: Viết lại câu hỏi tiếng Việt sao cho:
1. Rõ ràng, không mơ hồ
2. Nêu rõ thực thể (bảng, cột) liên quan nếu có thể đoán được
3. Nêu rõ điều kiện lọc, sắp xếp, giới hạn số kết quả
4. GIỮ NGUYÊN ngôn ngữ tiếng Việt
5. CHỈ trả về câu hỏi đã viết lại — KHÔNG giải thích, KHÔNG thêm gì khác

Ví dụ:
Input:  "top 3 sv gpa cao nhất cntt?"
Output: "Liệt kê 3 sinh viên có GPA cao nhất thuộc khoa Công nghệ thông tin, sắp xếp giảm dần theo GPA."
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "{user_question}"),
])


def rewriter_node(state: GraphState) -> dict:
    """LangGraph node: chuẩn hóa câu hỏi."""
    user_question = state["user_question"]

    try:
        llm = get_llm(max_tokens=256)
        chain = _prompt | llm | StrOutputParser()
        # LangChain tự retry khi dùng .with_retry()
        chain_with_retry = chain.with_retry(stop_after_attempt=3)
        rewritten = chain_with_retry.invoke({"user_question": user_question})
        rewritten = rewritten.strip()
        if not rewritten:
            raise ValueError("LLM trả về rỗng")
        logger.info("[Rewriter] %s → %s", user_question[:60], rewritten[:60])
        return {"rewritten_query": rewritten}
    except Exception as exc:
        logger.warning("[Rewriter] thất bại: %s — dùng câu gốc.", exc)
        return {"rewritten_query": user_question}