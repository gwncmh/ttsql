"""
ai/agents/nodes/query_rewriter.py
──────────────────────────────────
FIX:
- max_tokens tăng từ 256 → 512 để tránh response bị truncate
- Parser JSON cải thiện: dùng json.loads trực tiếp trước, fallback regex sau
- {{ }} escape đúng để LangChain không hiểu JSON example là template variable
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
{{"rewritten_query": "<câu hỏi đã viết lại>", "complexity": "SIMPLE hoặc COMPLEX"}}

Ví dụ 1:
Input:  "top 3 sv gpa cao nhất cntt?"
Output: {{"rewritten_query": "Liệt kê 3 sinh viên có GPA cao nhất thuộc khoa Công nghệ thông tin, sắp xếp giảm dần theo GPA.", "complexity": "SIMPLE"}}

Ví dụ 2:
Input:  "gpa trung bình mỗi khoa"
Output: {{"rewritten_query": "Tính GPA trung bình của sinh viên theo từng khoa, sắp xếp giảm dần.", "complexity": "COMPLEX"}}

Ví dụ 3:
Input:  "khoa nào có gpa trung bình cao nhất"
Output: {{"rewritten_query": "Tìm khoa có GPA trung bình cao nhất của sinh viên, tính bằng AVG(gpa) GROUP BY khoa.", "complexity": "COMPLEX"}}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "{user_question}"),
])


def _parse_json_response(raw: str) -> dict:
    """
    Parse JSON từ LLM response.
    Thử theo thứ tự:
    1. json.loads trực tiếp (nhanh nhất, xử lý được response sạch)
    2. Tìm block JSON đầu tiên trong text (xử lý được khi có text thừa)
    3. Regex relaxed hơn (xử lý được partial match)
    """
    raw = raw.strip()

    # Bước 1: thử parse trực tiếp
    try:
        data = json.loads(raw)
        return _validate_parsed(data)
    except (json.JSONDecodeError, ValueError):
        pass

    # Bước 2: tìm JSON block đầu tiên (kể cả khi có text trước/sau)
    # Dùng bộ đếm ngoặc để tìm đúng closing brace
    start = raw.find('{')
    if start != -1:
        depth = 0
        for i, ch in enumerate(raw[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(raw[start:i + 1])
                        return _validate_parsed(data)
                    except (json.JSONDecodeError, ValueError):
                        break

    # Bước 3: regex fallback — extract từng field riêng lẻ
    rewritten_match = re.search(
        r'"rewritten_query"\s*:\s*"([^"]+)"', raw
    )
    complexity_match = re.search(
        r'"complexity"\s*:\s*"(SIMPLE|COMPLEX)"', raw, re.IGNORECASE
    )
    if rewritten_match:
        return {
            "rewritten_query": rewritten_match.group(1).strip(),
            "complexity": (
                complexity_match.group(1).upper()
                if complexity_match else "SIMPLE"
            ),
        }

    return {}


def _validate_parsed(data: dict) -> dict:
    """Validate và normalize dict đã parse."""
    rewritten = data.get("rewritten_query", "").strip()
    complexity = data.get("complexity", "SIMPLE").strip().upper()
    if complexity not in ("SIMPLE", "COMPLEX"):
        complexity = "SIMPLE"
    if not rewritten:
        raise ValueError("rewritten_query rỗng")
    return {"rewritten_query": rewritten, "complexity": complexity}


def rewriter_node(state: GraphState) -> dict:
    """LangGraph node: viết lại câu hỏi + phân loại complexity trong 1 LLM call."""
    user_question = state["user_question"]

    try:
        # FIX: tăng max_tokens từ 256 → 512 để tránh response bị truncate
        llm = get_llm(max_tokens=512)
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

        logger.warning(
            "[Rewriter+Router] Không parse được JSON: %s — dùng fallback.", raw[:120]
        )
        return {"rewritten_query": user_question, "complexity": "SIMPLE"}

    except Exception as exc:
        logger.warning("[Rewriter+Router] LLM thất bại: %s — dùng fallback.", exc)
        return {"rewritten_query": user_question, "complexity": "SIMPLE"}


rewrite_query = rewriter_node