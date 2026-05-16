"""
ai/agents/pipeline.py
──────────────────────
Orchestrator nối toàn bộ 6 agent thành pipeline hoàn chỉnh.

Flow:
  user_question
    → [1] Query Rewriter     → rewritten_query
    → [2] Schema Retrieval   → schema_info, schema_text
    → [3] Adaptive Router    → complexity (SIMPLE | COMPLEX)
    → [4] SQL Generator      → sql, reasoning
    → [5] Execution+Feedback → rows, final_sql, retry_count, success
    → [6] Answer Generation  → answer
    → return dict
"""

import logging
import sys
from pathlib import Path

# Đảm bảo import hoạt động khi chạy từ bất kỳ thư mục nào
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.agents.query_rewriter    import rewrite_query      # noqa: E402
from ai.agents.schema_retrieval  import (                  # noqa: E402
    retrieve_schema, format_schema_for_prompt,
)
from ai.agents.adaptive_router   import classify_query     # noqa: E402
from ai.agents.sql_generator     import generate_sql       # noqa: E402
from ai.agents.execution_feedback import execute_with_feedback  # noqa: E402
from ai.agents.answer_generation  import generate_answer   # noqa: E402

logger = logging.getLogger(__name__)


def run_pipeline(user_question: str) -> dict[str, str]:
    """
    Chạy toàn bộ pipeline và trả về dict để ChatResponse consume.

    Keys trả về:
      rewritten_query, complexity, sql, answer
    """
    logger.info("=== Pipeline START: %s", user_question[:80])

    # ── Agent 1: Query Rewriter ───────────────────────────────────────────────
    rewritten = rewrite_query(user_question)
    logger.info("[1] Rewritten: %s", rewritten[:100])

    # ── Agent 2: Schema Retrieval ─────────────────────────────────────────────
    schema_info = retrieve_schema(rewritten)
    schema_text = format_schema_for_prompt(schema_info)
    logger.info(
        "[2] Schema: %d table(s) — %s",
        len(schema_info["tables"]),
        list(schema_info["tables"].keys()),
    )

    # ── Agent 3: Adaptive Router ──────────────────────────────────────────────
    complexity = classify_query(rewritten)
    logger.info("[3] Complexity: %s", complexity)

    # ── Agent 4: SQL Generator ────────────────────────────────────────────────
    sql, reasoning = generate_sql(rewritten, schema_text, complexity)
    logger.info("[4] SQL: %s", sql[:120])
    if reasoning:
        logger.debug("[4] Reasoning: %s", reasoning[:200])

    # ── Agent 5: Execution + Feedback ─────────────────────────────────────────
    exec_result = execute_with_feedback(sql, schema_text, rewritten)
    final_sql    = exec_result["final_sql"]
    rows         = exec_result["rows"]
    retry_count  = exec_result["retry_count"]
    success      = exec_result["success"]

    logger.info(
        "[5] Execution: success=%s, rows=%d, retries=%d",
        success, len(rows), retry_count,
    )

    # ── Agent 6: Answer Generation ────────────────────────────────────────────
    answer = generate_answer(
        user_question=user_question,
        rows=rows,
        execution_success=success,
        error_msg=exec_result.get("error"),
    )
    logger.info("[6] Answer: %s", answer[:100])
    logger.info("=== Pipeline END ===")

    return {
        "rewritten_query": rewritten,
        "complexity":      complexity,
        "sql":             final_sql,
        "answer":          answer,
    }