"""
ai/agents/execution_feedback.py
────────────────────────────────
Agent 5: Thực thi SQL trên SQLite, tự sửa lỗi tối đa MAX_RETRIES lần.

Feedback loop:
  Execute → Error? → Gọi LLM sửa SQL → Execute lại → ...
  Tối đa MAX_RETRIES = 3 lần sửa.
"""

import os
import logging
import re

import certifi
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 3


def _repair_sql(
    broken_sql: str,
    error_msg: str,
    schema_text: str,
    original_question: str,
) -> str:
    """Gọi LLM để sửa câu SQL bị lỗi."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return broken_sql  # không có key → trả lại nguyên để fail rõ ràng

    system = (
        "Bạn là chuyên gia sửa SQL cho SQLite.\n"
        "Phân tích lỗi, sửa câu SQL sao cho đúng.\n"
        "Chỉ trả về câu SQL đã sửa — KHÔNG giải thích, KHÔNG backtick."
    )
    user = (
        f"Schema:\n{schema_text}\n\n"
        f"Câu hỏi gốc: {original_question}\n\n"
        f"SQL lỗi:\n{broken_sql}\n\n"
        f"Lỗi SQLite:\n{error_msg}\n\n"
        "SQL đã sửa:"
    )
    model  = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    payload = {
        "model": model, "temperature": 0, "max_tokens": 256,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "http://localhost",
        "X-Title":       "TextToSQL",
    }
    verify = certifi.where()
    if os.getenv("OPENROUTER_SSL_VERIFY", "true").lower() in ("0", "false", "no"):
        verify = False

    try:
        with httpx.Client(timeout=30.0, verify=verify) as client:
            resp = client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload)
            resp.raise_for_status()
            fixed = resp.json()["choices"][0]["message"]["content"].strip()
            # Xóa backtick phòng khi model trả về dù đã dặn
            fixed = re.sub(r"```(?:sql)?", "", fixed, flags=re.IGNORECASE)
            fixed = fixed.replace("```", "").strip()
            return fixed
    except Exception as exc:
        logger.warning("Repair LLM thất bại: %s", exc)
        return broken_sql


def execute_with_feedback(
    sql: str,
    schema_text: str,
    original_question: str,
) -> dict:
    """
    Thực thi SQL, tự sửa lỗi tối đa MAX_RETRIES lần.

    Trả về:
    {
        "rows":         list[dict],      # kết quả truy vấn
        "final_sql":    str,             # SQL cuối cùng được chạy thành công
        "retry_count":  int,             # số lần sửa (0 = không cần sửa)
        "success":      bool,
        "error":        str | None,      # thông báo lỗi cuối cùng nếu thất bại
    }
    """
    # Import ở đây để tránh circular import khi test từng agent riêng
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from backend.app.db import execute_query

    current_sql = sql
    last_error:  str | None = None

    for attempt in range(MAX_RETRIES + 1):  # 0 = lần đầu, 1-3 = retry
        try:
            rows = execute_query(current_sql)
            logger.info(
                "Execution OK (attempt %d): %d row(s) returned.",
                attempt, len(rows),
            )
            return {
                "rows":        rows,
                "final_sql":   current_sql,
                "retry_count": attempt,
                "success":     True,
                "error":       None,
            }
        except (RuntimeError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "Execution attempt %d/%d failed: %s",
                attempt + 1, MAX_RETRIES + 1, last_error,
            )

            if attempt < MAX_RETRIES:
                logger.info("Đang sửa SQL...")
                current_sql = _repair_sql(
                    current_sql, last_error, schema_text, original_question
                )
            else:
                logger.error("Đã hết %d lần thử — trả về lỗi.", MAX_RETRIES)

    return {
        "rows":        [],
        "final_sql":   current_sql,
        "retry_count": MAX_RETRIES,
        "success":     False,
        "error":       last_error,
    }