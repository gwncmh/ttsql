"""
ai/agents/nodes/schema_retrieval.py
─────────────────────────────────────
Node 2 — Schema Retrieval (RAG-lite).

Cải tiến so với phiên bản cũ:
- Fallback thông minh: nếu LLM chọn 'students', tự động thêm 'majors'
  và 'faculties' vì gần như luôn cần để hiển thị tên thay vì ID số
- Timeout ngắn hơn cho schema selection (không cần max_tokens nhiều)
- Luôn include bảng có FK trực tiếp với bảng đã chọn

LangGraph node contract:
    Input : GraphState  (đọc "rewritten_query")
    Output: dict        (trả về {"schema_info": ..., "schema_text": ...})
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ai.agents.state import GraphState
from ai.agents.llm_client import get_llm

logger = logging.getLogger(__name__)

# FK relations tĩnh — phù hợp với schema init_db.py
_FK_RELATIONS = [
    ("students.major_id", "majors.id"),
    ("majors.faculty_id", "faculties.id"),
    ("scores.student_id", "students.id"),
]

# Bảng nào thì nên kéo theo bảng nào (để tránh trả về ID thô)
# Key: bảng được chọn → Value: bảng nên thêm vào
_AUTO_INCLUDE: dict[str, list[str]] = {
    "students": ["majors", "faculties"],
    "majors":   ["faculties"],
    "scores":   ["students"],
}

# ── Prompt ────────────────────────────────────────────────────────────────────
_SYSTEM = """\
Bạn là chuyên gia phân tích schema cơ sở dữ liệu.

Cho danh sách tất cả bảng trong DB và câu hỏi của người dùng,
hãy chọn ra các bảng CẦN THIẾT để viết SQL trả lời câu hỏi đó.

Quy tắc:
- Chỉ chọn bảng thực sự cần (liên quan đến câu hỏi)
- Nếu cần JOIN, thêm cả bảng trung gian
- Trả về JSON array tên bảng, ví dụ: ["students", "majors"]
- CHỈ trả về JSON array — KHÔNG thêm gì khác
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", (
        "Tất cả bảng trong DB:\n{all_tables}\n\n"
        "Câu hỏi: {rewritten_query}\n\n"
        "Bảng cần dùng (JSON array):"
    )),
])


def _get_full_schema() -> dict[str, list[str]]:
    """Đọc schema từ SQLite."""
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from backend.app.db import get_schema_info
    return get_schema_info()


def _expand_with_related(
    selected: list[str],
    full_schema: dict[str, list[str]],
) -> list[str]:
    """
    Tự động thêm bảng liên quan để tránh trả về ID số thô.
    Ví dụ: nếu chọn 'students' → thêm 'majors', 'faculties'.
    """
    result = list(selected)
    for table in list(selected):  # iterate bản copy để tránh infinite loop
        for related in _AUTO_INCLUDE.get(table, []):
            if related not in result and related in full_schema:
                result.append(related)
                logger.info(
                    "[Schema] Auto-include '%s' vì liên quan đến '%s'",
                    related, table,
                )
    return result


def _select_tables_with_llm(
    full_schema: dict[str, list[str]],
    rewritten_query: str,
) -> list[str]:
    """Dùng LLM để chọn bảng relevant."""
    all_tables_text = "\n".join(
        f"- {table}: ({', '.join(cols)})"
        for table, cols in full_schema.items()
    )
    try:
        llm = get_llm(max_tokens=64)   # chỉ cần JSON array ngắn
        chain = _prompt | llm | StrOutputParser()
        raw = chain.invoke({
            "all_tables": all_tables_text,
            "rewritten_query": rewritten_query,
        })
        raw = raw.strip()
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            tables = json.loads(match.group())
            valid = [t for t in tables if t in full_schema]
            if valid:
                logger.info("[Schema] LLM chọn bảng gốc: %s", valid)
                # Mở rộng với bảng liên quan
                expanded = _expand_with_related(valid, full_schema)
                if expanded != valid:
                    logger.info("[Schema] Sau auto-include: %s", expanded)
                return expanded
    except Exception as exc:
        logger.warning("[Schema] LLM chọn bảng thất bại: %s", exc)

    # Fallback: toàn bộ schema
    logger.info("[Schema] Fallback → dùng toàn bộ %d bảng", len(full_schema))
    return list(full_schema.keys())


def _format_schema_text(
    selected_tables: dict[str, list[str]],
    relations: list[tuple[str, str]],
) -> str:
    """Chuyển schema dict thành text cho LLM prompt."""
    lines = [
        f"Table: {table} ({', '.join(cols)})"
        for table, cols in selected_tables.items()
    ]
    for src, dst in relations:
        lines.append(f"FK: {src} → {dst}")
    return "\n".join(lines)


def schema_retrieval_node(state: GraphState) -> dict:
    """LangGraph node: truy xuất schema liên quan."""
    rewritten_query = state["rewritten_query"]

    try:
        full_schema = _get_full_schema()
    except Exception as exc:
        logger.error("[Schema] Không đọc được DB: %s", exc)
        return {
            "schema_info": {"tables": {}, "relations": [], "full_schema": {}},
            "schema_text": "",
            "error": f"Không đọc được schema: {exc}",
        }

    relevant_table_names = _select_tables_with_llm(full_schema, rewritten_query)
    selected_tables = {
        t: full_schema[t]
        for t in relevant_table_names
        if t in full_schema
    }

    relevant_fk = [
        (src, dst)
        for src, dst in _FK_RELATIONS
        if (
            src.split(".")[0] in selected_tables
            and dst.split(".")[0] in selected_tables
        )
    ]

    schema_info = {
        "tables": selected_tables,
        "relations": relevant_fk,
        "full_schema": full_schema,
    }
    schema_text = _format_schema_text(selected_tables, relevant_fk)

    logger.info(
        "[Schema] %d bảng cuối: %s",
        len(selected_tables),
        list(selected_tables.keys()),
    )
    return {"schema_info": schema_info, "schema_text": schema_text}