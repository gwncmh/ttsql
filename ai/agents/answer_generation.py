"""
ai/agents/answer_generation.py
───────────────────────────────
Agent 6: Chuyển kết quả SQL thành câu trả lời tiếng Việt tự nhiên.

Nếu LLM không khả dụng → dùng template đơn giản làm fallback.
"""

import os
import json
import logging

import certifi
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """\
Bạn là trợ lý trả lời câu hỏi về cơ sở dữ liệu sinh viên.

Nhiệm vụ: Dựa vào câu hỏi gốc và kết quả truy vấn SQL, viết câu trả lời:
- Bằng tiếng Việt, tự nhiên và thân thiện
- Trình bày dữ liệu rõ ràng (dùng danh sách đánh số nếu nhiều kết quả)
- Nếu kết quả rỗng: nói rõ không tìm thấy dữ liệu
- KHÔNG đề cập đến SQL hay database trong câu trả lời
- Độ dài vừa phải (2-6 dòng)
"""


def _fallback_answer(user_question: str, rows: list[dict]) -> str:
    """Template đơn giản khi không có LLM."""
    if not rows:
        return f"Không tìm thấy dữ liệu phù hợp với câu hỏi: {user_question}"

    if len(rows) == 1:
        row = rows[0]
        parts = [f"{k}: {v}" for k, v in row.items()]
        return "Kết quả: " + ", ".join(parts)

    lines = [f"Tìm thấy {len(rows)} kết quả:"]
    for i, row in enumerate(rows[:10], 1):
        parts = [f"{k}: {v}" for k, v in row.items()]
        lines.append(f"{i}. {', '.join(parts)}")
    if len(rows) > 10:
        lines.append(f"... và {len(rows) - 10} kết quả khác.")
    return "\n".join(lines)


def generate_answer(
    user_question: str,
    rows: list[dict],
    execution_success: bool,
    error_msg: str | None = None,
) -> str:
    """
    Sinh câu trả lời tự nhiên.
    Nếu execution thất bại → trả thông báo lỗi thân thiện.
    """
    if not execution_success:
        return (
            f"Xin lỗi, tôi không thể trả lời câu hỏi '{user_question}' lúc này. "
            f"Lỗi: {error_msg or 'Không xác định'}."
        )

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return _fallback_answer(user_question, rows)

    # Giới hạn rows gửi vào LLM để tránh vượt context
    rows_for_prompt = rows[:20]
    rows_json = json.dumps(rows_for_prompt, ensure_ascii=False, indent=2)

    user_content = (
        f"Câu hỏi: {user_question}\n\n"
        f"Kết quả truy vấn ({len(rows)} dòng, hiển thị tối đa 20):\n{rows_json}"
    )

    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    payload = {
        "model":       model,
        "temperature": 0.3,   # hơi sáng tạo một chút để câu trả lời tự nhiên
        "max_tokens":  400,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
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
            answer = resp.json()["choices"][0]["message"]["content"].strip()
            logger.debug("Answer generation OK: %s", answer[:80])
            return answer
    except Exception as exc:
        logger.warning("Answer LLM thất bại: %s — dùng fallback.", exc)
        return _fallback_answer(user_question, rows)