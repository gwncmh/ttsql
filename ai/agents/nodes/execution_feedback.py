"""
ai/agents/nodes/execution_feedback.py
───────────────────────────────────────
Node 5 — Execution + Feedback (Self-Correcting).

Feedback loop:
  Execute → Error? → LLM repair → Execute lại → ... (tối đa MAX_RETRIES)

Cải tiến so với phiên bản cũ:
- Repair chain là LangChain Runnable — dễ test, dễ swap prompt
- Không còn nested if/else, logic thẳng hơn
- Trạng thái retry rõ ràng hơn nhờ LangGraph state

LangGraph node contract:
    Input : GraphState  (đọc "sql", "schema_text", "rewritten_query")
    Output: dict        (trả về execution results + final_sql)
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ai.agents.state import GraphState
from ai.agents.llm_client import get_llm

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

# ── Repair prompt ─────────────────────────────────────────────────────────────
_SYSTEM_REPAIR = """\
Bạn là chuyên gia sửa lỗi SQL cho SQLite.

Nhận vào: SQL lỗi + thông báo lỗi SQLite + schema + câu hỏi gốc.
Nhiệm vụ: Phân tích lỗi và trả về SQL đã sửa — ĐÚNG HOÀN TOÀN.

Quy tắc:
- Chỉ dùng tên bảng và cột có trong schema
- Chỉ viết câu SELECT
- Chỉ trả về SQL thuần — KHÔNG backtick, KHÔNG giải thích
"""

_repair_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_REPAIR),
    ("human", (
        "Schema:\n{schema_text}\n\n"
        "Câu hỏi gốc: {original_question}\n\n"
        "SQL lỗi:\n{broken_sql}\n\n"
        "Lỗi SQLite:\n{error_msg}\n\n"
        "SQL đã sửa:"
    )),
])


def _clean_sql(raw: str) -> str:
    cleaned = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
    return cleaned.replace("```", "").strip()


def _repair_sql(
    broken_sql: str,
    error_msg: str,
    schema_text: str,
    original_question: str,
) -> str:
    """Gọi LangChain repair chain để sửa SQL lỗi."""
    try:
        llm = get_llm(max_tokens=256)
        chain = _repair_prompt | llm | StrOutputParser()
        raw = chain.invoke({
            "schema_text": schema_text,
            "original_question": original_question,
            "broken_sql": broken_sql,
            "error_msg": error_msg,
        })
        fixed = _clean_sql(raw)
        logger.info("[Repair] SQL mới: %s", fixed[:100])
        return fixed
    except Exception as exc:
        logger.warning("[Repair] LLM thất bại: %s — giữ SQL cũ.", exc)
        return broken_sql


def _execute_sql(sql: str) -> list[dict]:
    """Thực thi SQL qua backend db module."""
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from backend.app.db import execute_query
    return execute_query(sql)


def execution_feedback_node(state: GraphState) -> dict:
    """
    LangGraph node: thực thi SQL + tự sửa lỗi tối đa MAX_RETRIES lần.
    """
    current_sql = state.get("sql", "")
    schema_text = state.get("schema_text", "")
    original_question = state.get("rewritten_query", state.get("user_question", ""))

    if not current_sql:
        logger.error("[Executor] SQL rỗng — không thể thực thi.")
        return {
            "rows": [],
            "final_sql": current_sql,
            "retry_count": 0,
            "execution_success": False,
            "execution_error": "SQL rỗng — bước sinh SQL có thể đã thất bại.",
        }

    last_error: str | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            rows = _execute_sql(current_sql)
            logger.info(
                "[Executor] Thành công (attempt %d): %d dòng.",
                attempt, len(rows),
            )
            return {
                "rows": rows,
                "final_sql": current_sql,
                "retry_count": attempt,
                "execution_success": True,
                "execution_error": None,
            }
        except (RuntimeError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "[Executor] Attempt %d/%d lỗi: %s",
                attempt + 1, MAX_RETRIES + 1, last_error,
            )
            if attempt < MAX_RETRIES:
                current_sql = _repair_sql(
                    current_sql, last_error, schema_text, original_question
                )

    logger.error("[Executor] Đã hết %d lần thử.", MAX_RETRIES)
    return {
        "rows": [],
        "final_sql": current_sql,
        "retry_count": MAX_RETRIES,
        "execution_success": False,
        "execution_error": last_error,
    }