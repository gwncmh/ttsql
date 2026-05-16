"""
ai/agents/query_rewriter.py
───────────────────────────
Agent 1: Chuẩn hóa câu hỏi người dùng để dễ sinh SQL hơn.
- Gọi LLM qua OpenRouter
- Retry tối đa 3 lần với exponential backoff
- Fallback về câu gốc nếu LLM thất bại
"""

import os
import time
import warnings
import logging

import certifi
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """\
Bạn là chuyên gia chuẩn hóa câu hỏi cho hệ thống Text-to-SQL.

Nhiệm vụ: Viết lại câu hỏi tiếng Việt sao cho:
1. Rõ ràng, không mơ hồ
2. Nêu rõ thực thể (bảng, cột) liên quan nếu có thể đoán được
3. Nêu rõ điều kiện lọc, sắp xếp, giới hạn số kết quả
4. GIỮ NGUYÊN ngôn ngữ tiếng Việt
5. CHỈ trả về câu hỏi đã viết lại — KHÔNG giải thích, KHÔNG thêm gì khác

Ví dụ:
Input:  "top 3 sv gpa cao nhất cntt?"
Output: "Liệt kê 3 sinh viên có GPA cao nhất thuộc khoa Công nghệ thông tin, sắp xếp giảm dần theo GPA."
"""


def _ssl_verify_arg():
    flag = os.getenv("OPENROUTER_SSL_VERIFY", "true").strip().lower()
    if flag in ("0", "false", "no", "off"):
        warnings.warn(
            "TLS verification bị tắt (OPENROUTER_SSL_VERIFY=false). "
            "Chỉ dùng khi debug!",
            stacklevel=3,
        )
        return False
    for key in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        path = os.getenv(key)
        if path and os.path.isfile(path):
            return path
    return certifi.where()


def rewrite_query(user_query: str) -> str:
    """
    Chuẩn hóa câu hỏi, retry tối đa 3 lần.
    Fallback về câu gốc nếu tất cả lần thử đều thất bại.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY chưa được đặt — bỏ qua rewrite.")
        return user_query

    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 256,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_query},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "http://localhost",
        "X-Title":       "TextToSQL",
    }

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=30.0, verify=_ssl_verify_arg()) as client:
                resp = client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                result = data["choices"][0]["message"]["content"].strip()
                if result:
                    logger.debug("Rewriter OK (attempt %d): %s", attempt + 1, result[:80])
                    return result
        except Exception as exc:
            last_error = exc
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(
                "Rewriter attempt %d/%d failed: %s — retry in %ds",
                attempt + 1, 3, exc, wait,
            )
            time.sleep(wait)

    logger.error("Rewriter thất bại sau 3 lần: %s — dùng câu gốc.", last_error)
    return user_query