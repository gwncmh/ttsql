"""
ai/agents/nodes/query_rewriter.py
──────────────────────────────────
Node 1 — Query Rewriter + Complexity Classifier (merged).

Thay vì 2 LLM calls riêng (Rewriter → Router), node này gộp lại thành
1 call duy nhất trả về JSON với cả rewritten_query lẫn complexity.

Tiết kiệm ~1 LLM round-trip (~2-15s tuỳ free tier load).

LangGraph node contract:
    Input : GraphState  (đọc "user_question")
    Output: dict        (trả về {"rewritten_query": ..., "complexity": ...})
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ai.agents.state import GraphState
from ai.agents.llm_client import get_llm

logger = logging.getLogger(__name__)

# ── Prompt gộp rewrite + classify ────────────────────────────────────────────
_SYSTEM = """\
Bạn là chuyên gia xử lý câu hỏi cho hệ thống Text-to-SQL.

Nhiệm vụ: Với câu hỏi đầu vào, hãy thực hiện 2 việc cùng lúc:

1. VIẾT LẠI câu hỏi sao cho:
   - Rõ ràng, không mơ hồ
   - Nêu rõ thực thể (bảng, cột) liên quan nếu đoán được
   - Nêu rõ điều kiện lọc, sắp xếp, giới hạn số kết quả
   - Giữ nguyên tiếng Việt

2. PHÂN LOẠI độ phức tạp SQL cần thiết:
   - SIMPLE: SELECT đơn giản, tối đa 1-2 JOIN, không GROUP BY/HAVING, không subquery
   - COMPLEX: GROUP BY + HAVING, subquery/CTE, nhiều JOIN (3+), window functions,
              aggregation theo nhiều chiều (AVG/COUNT theo từng nhóm), so sánh chéo

Trả về JSON (KHÔNG thêm gì khác ngoài JSON):
{
  "rewritten_query": "<câu hỏi đã viết lại>",
  "complexity": "SIMPLE" hoặc "COMPLEX"
}

Ví dụ:
Input:  "top 3 sv gpa cao nhất cntt?"
Output: {"rewritten_query": "Liệt kê 3 sinh viên có GPA cao nhất thuộc khoa Công nghệ thông tin, sắp xếp giảm dần theo GPA.", "complexity": "SIMPLE"}

Input:  "gpa trung bình mỗi khoa"
Output: {"rewritten_query": "Tính GPA trung bình của sinh viên theo từng khoa, sắp xếp giảm dần.", "complexity": "COMPLEX"}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "{user_question}"),
])


def _parse_json_response(raw: str) -> dict:
    """Parse JSON từ LLM response, xử lý các trường hợp có text thừa."""
    raw = raw.strip()
    # Tìm JSON object trong response
    match = re.search(r'\{[^{}]*"rewritten_query"[^{}]*\}', raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            rewritten = data.get("rewritten_query", "").strip()
            complexity = data.get("complexity", "SIMPLE").strip().upper()
            if complexity not in ("SIMPLE", "COMPLEX"):
                complexity = "SIMPLE"
            if rewritten:
                return {"rewritten_query": rewritten, "complexity": complexity}
        except json.JSONDecodeError:
            pass
    return {}


def rewriter_node(state: GraphState) -> dict:
    """LangGraph node: viết lại câu hỏi + phân loại complexity trong 1 LLM call."""
    user_question = state["user_question"]

    try:
        llm = get_llm(max_tokens=256)
        chain = _prompt | llm | StrOutputParser()
        chain_with_retry = chain.with_retry(stop_after_attempt=2)
        raw = chain_with_retry.invoke({"user_question": user_question})
        raw = raw.strip()

        parsed = _parse_json_response(raw)
        if parsed:
            logger.info(
                "[Rewriter+Router] '%s' → '%s' [%s]",
                user_question[:50],
                parsed["rewritten_query"][:60],
                parsed["complexity"],
            )
            return parsed

        # Fallback: nếu không parse được JSON, dùng câu gốc + SIMPLE
        logger.warning("[Rewriter+Router] Không parse được JSON: %s — dùng fallback.", raw[:80])
        return {"rewritten_query": user_question, "complexity": "SIMPLE"}

    except Exception as exc:
        logger.warning("[Rewriter+Router] LLM thất bại: %s — dùng fallback.", exc)
        return {"rewritten_query": user_question, "complexity": "SIMPLE"}


# Giữ alias cũ để không break import nào khác
rewrite_query = rewriter_node