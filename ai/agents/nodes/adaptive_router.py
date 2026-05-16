"""
ai/agents/nodes/router.py
──────────────────────────
Node 3 — Adaptive Router.

Phân loại câu hỏi: SIMPLE hoặc COMPLEX.

Cải tiến so với phiên bản cũ:
- Không còn hardcode rule-based patterns
- Dùng LangChain với_structured_output (Pydantic) → type-safe
- LLM reasoning được ghi lại để debug
- Conditional edge của LangGraph routing dựa trên "complexity" field

LangGraph node contract:
    Input : GraphState  (đọc "rewritten_query")
    Output: dict        (trả về {"complexity": "SIMPLE" | "COMPLEX"})

Routing logic (conditional_edge trong graph.py):
    "SIMPLE"  → generate_sql_simple_node
    "COMPLEX" → generate_sql_cot_node
"""

from __future__ import annotations

import logging
from enum import Enum

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

from ai.agents.state import GraphState
from ai.agents.llm_client import get_llm_fast

logger = logging.getLogger(__name__)


# ── Structured output schema ───────────────────────────────────────────────────
class QueryComplexity(BaseModel):
    """Kết quả phân loại truy vấn."""
    complexity: str = Field(
        description="SIMPLE hoặc COMPLEX",
        pattern="^(SIMPLE|COMPLEX)$",
    )
    reason: str = Field(
        description="Lý do ngắn gọn (1 câu) tại sao phân loại như vậy",
    )


# ── Prompt ────────────────────────────────────────────────────────────────────
_SYSTEM = """\
Bạn là chuyên gia phân loại SQL query.

Phân loại câu hỏi thành SIMPLE hoặc COMPLEX dựa trên SQL cần thiết:

SIMPLE — khi SQL chỉ cần:
  • SELECT đơn giản với WHERE / ORDER BY / LIMIT
  • Tối đa 1-2 JOIN đơn giản
  • Không có aggregation GROUP BY/HAVING
  • Không có subquery hay CTE

COMPLEX — khi SQL cần:
  • GROUP BY + HAVING
  • Subquery hoặc CTE (WITH ... AS)
  • Nhiều JOIN (3+) hoặc JOIN phức tạp
  • Window functions (RANK, ROW_NUMBER...)
  • Set operations (UNION, INTERSECT, EXCEPT)
  • Aggregation theo nhiều chiều (AVG theo từng khoa, so sánh...)

Trả về JSON với 2 trường: complexity và reason.
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "Câu hỏi: {rewritten_query}"),
])


def router_node(state: GraphState) -> dict:
    """LangGraph node: phân loại độ phức tạp truy vấn."""
    rewritten_query = state["rewritten_query"]

    try:
        llm = get_llm_fast()
        # Dùng with_structured_output → trả về QueryComplexity object
        structured_llm = llm.with_structured_output(QueryComplexity)
        chain = _prompt | structured_llm
        result: QueryComplexity = chain.invoke(
            {"rewritten_query": rewritten_query}
        )
        complexity = result.complexity.upper()
        if complexity not in ("SIMPLE", "COMPLEX"):
            complexity = "SIMPLE"
        logger.info(
            "[Router] %s — lý do: %s",
            complexity,
            result.reason[:80],
        )
        return {"complexity": complexity}

    except Exception as exc:
        logger.warning("[Router] LLM thất bại: %s — fallback SIMPLE.", exc)
        return {"complexity": "SIMPLE"}


def route_by_complexity(state: GraphState) -> str:
    """
    Conditional edge function cho LangGraph.
    Trả về tên node tiếp theo dựa trên complexity.
    """
    return state.get("complexity", "SIMPLE")