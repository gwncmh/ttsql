"""
ai/agents/state.py
──────────────────
Định nghĩa GraphState — state duy nhất chạy xuyên suốt pipeline LangGraph.

Mỗi node đọc từ state và trả về dict để merge vào state hiện tại.
LangGraph sẽ tự động merge theo cơ chế add_messages / dict update.
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class GraphState(TypedDict, total=False):
    # ── Input ─────────────────────────────────────────────────────────────────
    user_question: str                  # câu hỏi gốc từ người dùng

    # ── Agent 1: Query Rewriter ───────────────────────────────────────────────
    rewritten_query: str                # câu hỏi đã được chuẩn hóa

    # ── Agent 2: Schema Retrieval ─────────────────────────────────────────────
    schema_info: dict[str, Any]         # {"tables": {...}, "relations": [...]}
    schema_text: str                    # schema dạng text để đưa vào prompt

    # ── Agent 3: Adaptive Router ──────────────────────────────────────────────
    complexity: str                     # "SIMPLE" | "COMPLEX"

    # ── Agent 4: SQL Generator ────────────────────────────────────────────────
    sql: str                            # câu SQL được sinh ra
    reasoning: str                      # reasoning từ CoT (nếu có)

    # ── Agent 5: Execution + Feedback ─────────────────────────────────────────
    rows: list[dict]                    # kết quả truy vấn
    final_sql: str                      # SQL cuối cùng thực thi thành công
    retry_count: int                    # số lần tự sửa
    execution_success: bool             # True nếu chạy thành công
    execution_error: Optional[str]      # thông báo lỗi nếu thất bại

    # ── Agent 6: Answer Generation ────────────────────────────────────────────
    answer: str                         # câu trả lời tiếng Việt tự nhiên

    # ── Meta ──────────────────────────────────────────────────────────────────
    error: Optional[str]                # lỗi nghiêm trọng làm dừng pipeline