"""
ai/agents/nodes/sql_generator.py
──────────────────────────────────
Node 4 — SQL Generator (hai chế độ).

SIMPLE  → 1-shot chain: prompt | llm | StrOutputParser | sql_cleaner
COMPLEX → CoT chain:    prompt | llm | StrOutputParser | cot_extractor

Cải tiến so với phiên bản cũ:
- Mỗi chain là một LangChain Runnable thuần — dễ test riêng lẻ
- SQL cleaning tách thành hàm riêng (không lẫn với logic)
- CoT extractor dùng regex nhưng được đóng gói gọn
- Không còn if/else lồng nhau, logic rõ ràng hơn

LangGraph node contract:
    Input : GraphState  (đọc "rewritten_query", "schema_text", "complexity")
    Output: dict        (trả về {"sql": ..., "reasoning": ...})
"""

from __future__ import annotations

import re
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from ai.agents.state import GraphState
from ai.agents.llm_client import get_llm

logger = logging.getLogger(__name__)


# ── SQL cleaner ───────────────────────────────────────────────────────────────
def _clean_sql(raw: str) -> str:
    """Xóa backtick và markdown code fence còn sót lại."""
    cleaned = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()
    return cleaned


# ── CoT extractor ─────────────────────────────────────────────────────────────
def _extract_cot(raw: str) -> dict:
    """
    Tách ANALYSIS và SQL từ CoT output.
    Trả về {"sql": ..., "reasoning": ...}
    """
    # Tìm phần SQL
    sql_match = re.search(
        r"SQL:\s*\n([\s\S]+?)(?:\n\n|$)", raw, re.IGNORECASE
    )
    if sql_match:
        sql = sql_match.group(1).strip()
    else:
        # Fallback: tìm code fence
        fence = re.search(r"```(?:sql)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
        if fence:
            sql = fence.group(1).strip()
        else:
            # Fallback cuối: lấy từ SELECT
            idx = raw.upper().find("SELECT")
            sql = raw[idx:].strip() if idx >= 0 else raw.strip()

    # Tìm phần ANALYSIS
    analysis_match = re.search(
        r"ANALYSIS:\s*\n([\s\S]+?)(?:\nSQL:|$)", raw, re.IGNORECASE
    )
    reasoning = analysis_match.group(1).strip() if analysis_match else ""

    return {"sql": _clean_sql(sql), "reasoning": reasoning}


# ── Prompt: 1-shot ────────────────────────────────────────────────────────────
_SYSTEM_1SHOT = """\
Bạn là chuyên gia viết SQL cho SQLite.

Quy tắc:
1. Chỉ dùng tên bảng và cột có trong schema được cung cấp
2. Chỉ viết câu SELECT — KHÔNG INSERT/UPDATE/DELETE
3. Dùng JOIN đúng theo foreign key
4. LIMIT hợp lý nếu câu hỏi yêu cầu "top N" hoặc "một vài"
5. Alias bảng ngắn gọn (s, m, f, sc)
6. Chỉ trả về SQL thuần — KHÔNG giải thích, KHÔNG markdown, KHÔNG backtick
"""

_prompt_1shot = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_1SHOT),
    ("human", (
        "Schema cơ sở dữ liệu:\n{schema_text}\n\n"
        "Câu hỏi: {rewritten_query}\n\n"
        "Viết câu SQL:"
    )),
])

# ── Prompt: Chain-of-Thought ──────────────────────────────────────────────────
_SYSTEM_COT = """\
Bạn là chuyên gia viết SQL phức tạp cho SQLite.

Quy trình bắt buộc:
1. Phân tích câu hỏi: xác định thực thể, điều kiện, phép tính
2. Lên kế hoạch JOIN / GROUP BY / HAVING / subquery nếu cần
3. Viết SQL hoàn chỉnh

Output format bắt buộc (không được thay đổi):
ANALYSIS:
<phân tích ngắn gọn, 2-4 dòng>

SQL:
<câu SQL hoàn chỉnh, không backtick, không markdown>
"""

_prompt_cot = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_COT),
    ("human", (
        "Schema cơ sở dữ liệu:\n{schema_text}\n\n"
        "Câu hỏi: {rewritten_query}"
    )),
])


# ── Build chains ──────────────────────────────────────────────────────────────
def _build_simple_chain():
    llm = get_llm(max_tokens=512)
    return (
        _prompt_1shot
        | llm
        | StrOutputParser()
        | RunnableLambda(lambda raw: {
            "sql": _clean_sql(raw),
            "reasoning": "",
        })
    )


def _build_cot_chain():
    llm = get_llm(max_tokens=768)
    return (
        _prompt_cot
        | llm
        | StrOutputParser()
        | RunnableLambda(_extract_cot)
    )


# ── Nodes ─────────────────────────────────────────────────────────────────────
def generate_sql_simple_node(state: GraphState) -> dict:
    """LangGraph node: sinh SQL kiểu 1-shot (SIMPLE query)."""
    try:
        chain = _build_simple_chain()
        result = chain.invoke({
            "schema_text": state["schema_text"],
            "rewritten_query": state["rewritten_query"],
        })
        logger.info("[SQL/1-shot] %s", result["sql"][:100])
        return result  # {"sql": ..., "reasoning": ""}
    except Exception as exc:
        logger.error("[SQL/1-shot] Lỗi: %s", exc)
        return {"sql": "", "reasoning": "", "error": str(exc)}


def generate_sql_cot_node(state: GraphState) -> dict:
    """LangGraph node: sinh SQL kiểu Chain-of-Thought (COMPLEX query)."""
    try:
        chain = _build_cot_chain()
        result = chain.invoke({
            "schema_text": state["schema_text"],
            "rewritten_query": state["rewritten_query"],
        })
        logger.info("[SQL/CoT] %s", result["sql"][:100])
        if result.get("reasoning"):
            logger.debug("[SQL/CoT] Reasoning: %s", result["reasoning"][:200])
        return result  # {"sql": ..., "reasoning": ...}
    except Exception as exc:
        logger.error("[SQL/CoT] Lỗi: %s", exc)
        return {"sql": "", "reasoning": "", "error": str(exc)}