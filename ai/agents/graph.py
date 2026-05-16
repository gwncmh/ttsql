"""
ai/agents/graph.py
───────────────────
Định nghĩa LangGraph StateGraph — orchestrator chính.

Flow:
  START
    → rewriter          (Query Rewriter)
    → schema_retrieval  (Schema Retrieval)
    → router            (Adaptive Router)
    → [conditional]
        "SIMPLE"  → generate_sql_simple
        "COMPLEX" → generate_sql_cot
    → execution_feedback (Execution + Self-Repair)
    → answer_generation  (NLG)
  END

Cách dùng:
    from ai.agents.graph import build_graph

    app = build_graph()
    result = app.invoke({"user_question": "Top 3 sinh viên GPA cao nhất?"})
    print(result["answer"])
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END

from ai.agents.state import GraphState
from ai.agents.nodes.query_rewriter import rewriter_node
from ai.agents.nodes.schema_retrieval import schema_retrieval_node
from ai.agents.nodes.adaptive_router import router_node, route_by_complexity
from ai.agents.nodes.sql_generator import (
    generate_sql_simple_node,
    generate_sql_cot_node,
)
from ai.agents.nodes.execution_feedback import execution_feedback_node
from ai.agents.nodes.answer_generation import answer_generation_node

logger = logging.getLogger(__name__)


def build_graph() -> "CompiledGraph":
    """
    Xây dựng và compile LangGraph StateGraph.

    Returns:
        Compiled graph sẵn sàng để .invoke() hoặc .stream()
    """
    builder = StateGraph(GraphState)

    # ── Đăng ký nodes ─────────────────────────────────────────────────────────
    builder.add_node("rewriter",           rewriter_node)
    builder.add_node("schema_retrieval",   schema_retrieval_node)
    builder.add_node("router",             router_node)
    builder.add_node("generate_sql_simple", generate_sql_simple_node)
    builder.add_node("generate_sql_cot",   generate_sql_cot_node)
    builder.add_node("execution_feedback", execution_feedback_node)
    builder.add_node("answer_generation",  answer_generation_node)

    # ── Edges tuyến tính ───────────────────────────────────────────────────────
    builder.add_edge(START,              "rewriter")
    builder.add_edge("rewriter",         "schema_retrieval")
    builder.add_edge("schema_retrieval", "router")

    # ── Conditional edge: router → SQL generator ───────────────────────────────
    builder.add_conditional_edges(
        "router",
        route_by_complexity,          # fn(state) → "SIMPLE" | "COMPLEX"
        {
            "SIMPLE":  "generate_sql_simple",
            "COMPLEX": "generate_sql_cot",
        },
    )

    # ── Merge hai SQL branches → execution ────────────────────────────────────
    builder.add_edge("generate_sql_simple", "execution_feedback")
    builder.add_edge("generate_sql_cot",    "execution_feedback")

    # ── Tiếp tục đến answer → END ─────────────────────────────────────────────
    builder.add_edge("execution_feedback",  "answer_generation")
    builder.add_edge("answer_generation",   END)

    compiled = builder.compile()
    logger.info("LangGraph compiled thành công.")
    return compiled


# Singleton graph instance — lazy init để tránh import cycle
_graph_instance = None


def get_graph():
    """Trả về compiled graph (singleton, lazy init)."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance