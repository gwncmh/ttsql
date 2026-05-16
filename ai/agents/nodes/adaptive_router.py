"""
ai/agents/nodes/adaptive_router.py
────────────────────────────────────
Node 3 — Adaptive Router (no LLM).

Sau khi merge Rewriter + Classifier thành 1 node, Router không cần
gọi LLM nữa — complexity đã có sẵn trong state từ rewriter_node.

Node này chỉ còn đọc state và log để dễ debug.

LangGraph node contract:
    Input : GraphState  (đọc "complexity" — đã được set bởi rewriter_node)
    Output: dict        (trả về {"complexity": ...} — giữ nguyên, không đổi)

Conditional edge function route_by_complexity() giữ nguyên để graph.py
không cần thay đổi.
"""

from __future__ import annotations

import logging

from ai.agents.state import GraphState

logger = logging.getLogger(__name__)


def router_node(state: GraphState) -> dict:
    """
    LangGraph node: đọc complexity từ state (đã set bởi rewriter_node).
    Không gọi LLM — tiết kiệm 1 round-trip.
    """
    complexity = state.get("complexity", "SIMPLE").upper()
    if complexity not in ("SIMPLE", "COMPLEX"):
        complexity = "SIMPLE"

    logger.info("[Router] complexity từ state: %s", complexity)
    return {"complexity": complexity}


def route_by_complexity(state: GraphState) -> str:
    """
    Conditional edge function cho LangGraph.
    Trả về tên node tiếp theo dựa trên complexity.
    """
    return state.get("complexity", "SIMPLE")