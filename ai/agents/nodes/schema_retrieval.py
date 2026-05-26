"""
ai/agents/nodes/schema_retrieval.py
─────────────────────────────────────
Node 2 — Schema Retrieval (RAG-lite).

- Đọc schema từ DB đang active qua db_manager
- FK tự suy luận từ _id convention (không hardcode)
- Auto-include bảng liên quan động theo FK
"""

from __future__ import annotations

import importlib
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


# ── Đọc schema từ DB đang active ─────────────────────────────────────────────
def _get_full_schema() -> dict[str, list[str]]:
    """
    Đọc schema từ DB đang active.

    Dùng importlib + sys.modules để đảm bảo nhận ĐÚNG module object
    mà upload.py đã gọi set_active_db() — tránh trường hợp Python
    load hai instance khác nhau của cùng một module.
    """
    # Đảm bảo PROJECT_ROOT trong sys.path để import backend.*
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    # Thử import db_manager theo cả hai path có thể có
    for mod_name in ("backend.app.db_manager", "app.db_manager"):
        try:
            mod = importlib.import_module(mod_name)
            schema = mod.get_active_schema()
            logger.info(
                "[Schema] Dùng %s | DB: %s | %d bảng: %s",
                mod_name,
                mod.get_active_path(),
                len(schema),
                list(schema.keys()),
            )
            return schema
        except ImportError:
            continue
        except Exception as exc:
            logger.error("[Schema] Lỗi khi gọi %s.get_active_schema(): %s", mod_name, exc)
            raise

    # Fallback cuối: db.py tĩnh (luôn là university.db)
    logger.warning("[Schema] Không import được db_manager — fallback về db.py (university.db cố định)")
    from backend.app.db import get_schema_info
    return get_schema_info()


# ── Suy luận FK từ _id convention ────────────────────────────────────────────
def _infer_fk_relations(schema: dict[str, list[str]]) -> list[tuple[str, str]]:
    """
    Suy luận FK từ tên cột dạng <prefix>_id.
    Thử các biến thể: prefix, prefix+s, prefix+es, prefix(y→ies).
    """
    relations = []
    table_names = set(schema.keys())

    for table, cols in schema.items():
        for col in cols:
            if not col.endswith("_id") or col == "id":
                continue
            prefix = col[:-3]
            candidates = [
                prefix,
                prefix + "s",
                prefix + "es",
                prefix.rstrip("y") + "ies" if prefix.endswith("y") else None,
            ]
            for candidate in candidates:
                if candidate and candidate in table_names:
                    relations.append((f"{table}.{col}", f"{candidate}.id"))
                    break

    return relations


# ── Build auto-include map ────────────────────────────────────────────────────
def _build_auto_include(fk_relations: list[tuple[str, str]]) -> dict[str, list[str]]:
    """table → [related tables] để tự động include bảng lookup."""
    auto: dict[str, list[str]] = {}
    for src, dst in fk_relations:
        src_t = src.split(".")[0]
        dst_t = dst.split(".")[0]
        auto.setdefault(src_t, [])
        if dst_t not in auto[src_t]:
            auto[src_t].append(dst_t)
    return auto


def _expand_with_related(
    selected: list[str],
    full_schema: dict[str, list[str]],
    auto_include: dict[str, list[str]],
) -> list[str]:
    result = list(selected)
    for table in list(selected):
        for related in auto_include.get(table, []):
            if related not in result and related in full_schema:
                result.append(related)
                logger.info("[Schema] Auto-include '%s' vì liên quan đến '%s'", related, table)
    return result


# ── Prompt ────────────────────────────────────────────────────────────────────
_SYSTEM = """\
Bạn là chuyên gia phân tích schema cơ sở dữ liệu.

Cho danh sách tất cả bảng trong DB và câu hỏi của người dùng,
hãy chọn ra các bảng CẦN THIẾT để viết SQL trả lời câu hỏi đó.

Quy tắc:
- Chỉ chọn bảng thực sự cần (liên quan đến câu hỏi)
- Nếu cần JOIN, thêm cả bảng trung gian
- Trả về JSON array tên bảng, ví dụ: ["members", "cards"]
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


# ── LLM table selector ────────────────────────────────────────────────────────
def _select_tables_with_llm(
    full_schema: dict[str, list[str]],
    rewritten_query: str,
    auto_include: dict[str, list[str]],
) -> list[str]:
    all_tables_text = "\n".join(
        f"- {table}: ({', '.join(cols)})"
        for table, cols in full_schema.items()
    )
    try:
        llm = get_llm(max_tokens=64)
        chain = _prompt | llm | StrOutputParser()
        raw = chain.invoke({
            "all_tables": all_tables_text,
            "rewritten_query": rewritten_query,
        })
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            tables = json.loads(match.group())
            valid = [t for t in tables if t in full_schema]
            if valid:
                logger.info("[Schema] LLM chọn: %s", valid)
                expanded = _expand_with_related(valid, full_schema, auto_include)
                if expanded != valid:
                    logger.info("[Schema] Sau auto-include: %s", expanded)
                return expanded
    except Exception as exc:
        logger.warning("[Schema] LLM thất bại: %s", exc)

    logger.info("[Schema] Fallback → toàn bộ %d bảng", len(full_schema))
    return list(full_schema.keys())


# ── Format schema text ────────────────────────────────────────────────────────
def _format_schema_text(
    selected_tables: dict[str, list[str]],
    relations: list[tuple[str, str]],
) -> str:
    lines = [
        f"Table: {table} ({', '.join(cols)})"
        for table, cols in selected_tables.items()
    ]
    for src, dst in relations:
        lines.append(f"FK: {src} → {dst}")
    return "\n".join(lines)


# ── LangGraph node ────────────────────────────────────────────────────────────
def schema_retrieval_node(state: GraphState) -> dict:
    """LangGraph node: truy xuất schema từ DB đang active."""
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

    fk_relations = _infer_fk_relations(full_schema)
    auto_include = _build_auto_include(fk_relations)
    logger.info("[Schema] FK suy luận được: %s", fk_relations)

    relevant_table_names = _select_tables_with_llm(full_schema, rewritten_query, auto_include)
    selected_tables = {t: full_schema[t] for t in relevant_table_names if t in full_schema}

    relevant_fk = [
        (src, dst) for src, dst in fk_relations
        if src.split(".")[0] in selected_tables and dst.split(".")[0] in selected_tables
    ]

    schema_info = {
        "tables": selected_tables,
        "relations": relevant_fk,
        "full_schema": full_schema,
    }
    schema_text = _format_schema_text(selected_tables, relevant_fk)

    logger.info("[Schema] Kết quả: %d bảng: %s", len(selected_tables), list(selected_tables.keys()))
    return {"schema_info": schema_info, "schema_text": schema_text}