"""
ai/agents/sql_generator.py
───────────────────────────
Agent 4: Sinh câu lệnh SQL từ câu hỏi đã rewrite + schema.

Hai chế độ:
  SIMPLE  → 1-shot: chỉ yêu cầu SQL, không cần reasoning trung gian
  COMPLEX → Chain-of-Thought: yêu cầu LLM giải thích từng bước rồi mới cho SQL
"""

import os
import re
import logging

import certifi
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── System prompts ────────────────────────────────────────────────────────────

SYSTEM_1SHOT = """\
Bạn là chuyên gia viết SQL cho SQLite.

Quy tắc:
1. Chỉ dùng tên bảng và cột có trong schema được cung cấp
2. Chỉ viết câu SELECT — KHÔNG INSERT/UPDATE/DELETE
3. Dùng JOIN đúng theo foreign key
4. LIMIT hợp lý nếu câu hỏi yêu cầu "top N" hoặc "một vài"
5. Alias bảng ngắn gọn (s, m, f, sc)
6. Chỉ trả về SQL — KHÔNG giải thích, KHÔNG markdown, KHÔNG backtick
"""

SYSTEM_COT = """\
Bạn là chuyên gia viết SQL phức tạp cho SQLite.

Quy trình (bắt buộc):
1. Phân tích câu hỏi: xác định thực thể, điều kiện, phép tính cần thiết
2. Lên kế hoạch JOIN/GROUP BY/HAVING nếu cần
3. Viết SQL hoàn chỉnh

Output format bắt buộc:
ANALYSIS:
<phân tích ngắn gọn, 2-4 dòng>

SQL:
<câu SQL hoàn chỉnh, không backtick>
"""


def _call_llm(system: str, user: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY chưa được đặt.")

    model   = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    payload = {
        "model":       model,
        "temperature": 0,
        "max_tokens":  512,
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

    with httpx.Client(timeout=45.0, verify=verify) as client:
        resp = client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


def _extract_sql_from_cot(raw: str) -> str:
    """
    Lấy phần SQL từ output Chain-of-Thought.
    Tìm block sau "SQL:" hoặc code fence ```sql...```.
    """
    # Thử tìm block sau "SQL:"
    match = re.search(r"SQL:\s*\n([\s\S]+?)(?:\n\n|$)", raw, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Thử tìm code fence
    fence = re.search(r"```(?:sql)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()

    # Fallback: lấy dòng có chứa SELECT
    for line in raw.splitlines():
        if "SELECT" in line.upper():
            # Lấy từ dòng SELECT đến hết
            idx = raw.upper().find("SELECT")
            return raw[idx:].strip()

    return raw.strip()


def generate_sql(
    rewritten_query: str,
    schema_text: str,
    complexity: str,
) -> tuple[str, str]:
    """
    Sinh SQL và trả về (sql, reasoning).
    reasoning = "" với 1-shot, hoặc phần ANALYSIS với CoT.
    """
    if complexity == "COMPLEX":
        user_prompt = (
            f"Schema cơ sở dữ liệu:\n{schema_text}\n\n"
            f"Câu hỏi: {rewritten_query}"
        )
        raw = _call_llm(SYSTEM_COT, user_prompt)
        sql = _extract_sql_from_cot(raw)

        # Tách reasoning
        reasoning_match = re.search(
            r"ANALYSIS:\s*\n([\s\S]+?)(?:\nSQL:|$)", raw, re.IGNORECASE
        )
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

        logger.debug("SQL Generator (CoT) → %s", sql[:120])
        return sql, reasoning

    else:  # SIMPLE → 1-shot
        user_prompt = (
            f"Schema cơ sở dữ liệu:\n{schema_text}\n\n"
            f"Câu hỏi: {rewritten_query}\n\n"
            "Viết câu SQL:"
        )
        sql = _call_llm(SYSTEM_1SHOT, user_prompt)

        # Xóa backtick nếu model vẫn trả về dù đã dặn
        sql = re.sub(r"```(?:sql)?", "", sql, flags=re.IGNORECASE).replace("```", "").strip()

        logger.debug("SQL Generator (1-shot) → %s", sql[:120])
        return sql, ""