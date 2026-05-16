"""
ai/agents/pipeline.py
──────────────────────
Entry point cho toàn bộ AI pipeline — giờ là thin wrapper quanh LangGraph.

API giữ nguyên để backend không cần thay đổi:
    from ai.agents.pipeline import run_pipeline
    result = run_pipeline(user_question="Top 3 sinh viên GPA cao nhất?")
    # result: {"rewritten_query", "complexity", "sql", "answer"}

Thay đổi nội bộ:
- Pipeline cũ: 6 hàm Python gọi nhau thủ công với if/else routing
- Pipeline mới: LangGraph StateGraph với typed state, conditional edges,
  built-in retry (via LangChain chains), và dễ mở rộng thêm node mới
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Đảm bảo import hoạt động khi chạy từ bất kỳ thư mục nào
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.agents.graph import get_graph  # noqa: E402

logger = logging.getLogger(__name__)


def run_pipeline(user_question: str) -> dict[str, str]:
    """
    Chạy toàn bộ pipeline qua LangGraph và trả về dict.

    Keys trả về (tương thích với ChatResponse schema):
        rewritten_query, complexity, sql, answer
    """
    logger.info("=== Pipeline START (LangGraph): %s", user_question[:80])

    graph = get_graph()

    # Invoke LangGraph — trả về GraphState đầy đủ
    final_state = graph.invoke({"user_question": user_question})

    logger.info(
        "=== Pipeline END — complexity=%s, sql_len=%d, answer_len=%d",
        final_state.get("complexity"),
        len(final_state.get("sql", "") or ""),
        len(final_state.get("answer", "") or ""),
    )

    return {
        "rewritten_query": final_state.get("rewritten_query", user_question),
        "complexity":      final_state.get("complexity", "SIMPLE"),
        "sql":             final_state.get("final_sql") or final_state.get("sql", ""),
        "answer":          final_state.get("answer", "Không có câu trả lời."),
        "rows":            final_state.get("rows", []),   # <-- thêm dòng này
    }