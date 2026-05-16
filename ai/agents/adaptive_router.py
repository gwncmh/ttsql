"""
ai/agents/adaptive_router.py
─────────────────────────────
Agent 3: Phân loại độ phức tạp truy vấn → SIMPLE hoặc COMPLEX.

Chiến lược hai lớp:
  Lớp 1 (nhanh) — Rule-based: nhận diện pattern rõ ràng → không cần LLM
  Lớp 2 (chính xác) — LLM classify: dùng khi rule-based không chắc
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

# Patterns dứt khoát là COMPLEX
COMPLEX_PATTERNS = [
    r"\bgroup\s+by\b",
    r"\bhaving\b",
    r"\bunion\b",
    r"\bintersect\b",
    r"\bexcept\b",
    r"\bsubquery\b",
    r"\bwith\b.*\bas\b",   # CTE
    r"\btrung\s+bình\b",   # tiếng Việt: "trung bình" → AVG thường cần GROUP BY
    r"\btheo\s+từng\b",    # "theo từng khoa/ngành" → GROUP BY
    r"\bmỗi\b",            # "mỗi khoa" → GROUP BY
    r"\btỉ\s+lệ\b",        # "tỉ lệ" → phức tạp
    r"\bso\s+sánh\b",      # "so sánh" → phức tạp
    r"\bnhiều\s+bảng\b",
    r"\bjoin\b",
]

# Patterns dứt khoát là SIMPLE
SIMPLE_PATTERNS = [
    r"\btop\s+\d+\b",           # "top 3 sinh viên"
    r"\bliệt\s+kê\b",           # "liệt kê sinh viên"
    r"\bcho\s+biết\b",          # "cho biết tên"
    r"\bnhững\s+ai\b",          # "những ai có GPA > 3.5"
    r"\bnhững\s+sinh\s+viên\b",
    r"\bcao\s+nhất\b",          # "GPA cao nhất" không kèm GROUP BY
    r"\bthấp\s+nhất\b",
]


def _rule_based_classify(query: str) -> str | None:
    """
    Trả về "COMPLEX", "SIMPLE", hoặc None nếu không chắc.
    """
    q = query.lower()
    for pat in COMPLEX_PATTERNS:
        if re.search(pat, q):
            return "COMPLEX"
    # SIMPLE chỉ kết luận nếu KHÔNG có bất kỳ dấu hiệu complex nào
    for pat in SIMPLE_PATTERNS:
        if re.search(pat, q):
            return "SIMPLE"
    return None


def _llm_classify(query: str) -> str:
    """
    Gọi LLM để phân loại. Fallback về "SIMPLE" nếu thất bại.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "SIMPLE"

    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    system = (
        "Phân loại câu hỏi SQL là SIMPLE hoặc COMPLEX.\n"
        "SIMPLE: SELECT đơn, ít/không JOIN, không GROUP BY/HAVING/subquery.\n"
        "COMPLEX: có GROUP BY, HAVING, subquery, nhiều JOIN, set operations.\n"
        "Chỉ trả về đúng một trong hai từ: SIMPLE hoặc COMPLEX."
    )
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 10,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": query},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "http://localhost",
        "X-Title":       "TextToSQL",
    }

    try:
        import ssl as _ssl
        verify = certifi.where()
        ssl_flag = os.getenv("OPENROUTER_SSL_VERIFY", "true").lower()
        if ssl_flag in ("0", "false", "no", "off"):
            verify = False
        with httpx.Client(timeout=15.0, verify=verify) as client:
            resp = client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip().upper()
            return "COMPLEX" if "COMPLEX" in raw else "SIMPLE"
    except Exception as exc:
        logger.warning("Router LLM thất bại: %s — dùng SIMPLE.", exc)
        return "SIMPLE"


def classify_query(rewritten_query: str) -> str:
    """
    Phân loại câu hỏi: "SIMPLE" hoặc "COMPLEX".
    Dùng rule-based trước, LLM nếu không chắc.
    """
    rule_result = _rule_based_classify(rewritten_query)
    if rule_result is not None:
        logger.debug("Router rule-based: %s", rule_result)
        return rule_result

    llm_result = _llm_classify(rewritten_query)
    logger.debug("Router LLM: %s", llm_result)
    return llm_result