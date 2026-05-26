"""
ai/agents/llm_client.py
────────────────────────
FIX:
- TLS warning chỉ hiện 1 lần khi module load, không lặp lại mỗi request
- Cache verify config để không tính lại mỗi lần get_llm() gọi
"""

from __future__ import annotations

import os
import warnings
import certifi
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_DEFAULT_HEADERS = {
    "HTTP-Referer": "http://localhost",
    "X-Title": "TextToSQL",
}


def _get_verify() -> str | bool:
    """Trả về cấu hình TLS verify. Chỉ warn một lần nhờ warnings.warn default filter."""
    flag = os.getenv("OPENROUTER_SSL_VERIFY", "true").strip().lower()
    if flag in ("0", "false", "no", "off"):
        # FIX: dùng warnings.warn với category=UserWarning ở module level effect
        # stacklevel=2 trỏ về caller, nhưng quan trọng là chỉ warn 1 lần nhờ
        # Python default filter "once" per location
        warnings.warn(
            "TLS verification bị tắt (OPENROUTER_SSL_VERIFY=false). "
            "Chỉ dùng khi debug!",
            UserWarning,
            stacklevel=2,
        )
        return False
    for key in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        path = os.getenv(key)
        if path and os.path.isfile(path):
            return path
    return certifi.where()


# FIX: tính verify config một lần khi module load, không tính lại mỗi get_llm()
_VERIFY = _get_verify()

# FIX: cache http_client để tránh tạo mới mỗi request
_HTTP_CLIENT = None


def _get_http_client():
    """Lazy init http_client, cache singleton."""
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None:
        return _HTTP_CLIENT

    if _VERIFY is False:
        import httpx
        _HTTP_CLIENT = httpx.Client(verify=False)
    elif isinstance(_VERIFY, str):
        import httpx
        import ssl as _ssl
        ctx = _ssl.create_default_context(cafile=_VERIFY)
        _HTTP_CLIENT = httpx.Client(ssl_context=ctx)
    else:
        _HTTP_CLIENT = None  # dùng default

    return _HTTP_CLIENT


def get_llm(
    temperature: float = 0,
    max_tokens: int = 512,
) -> ChatOpenAI:
    """Trả về ChatOpenAI instance kết nối OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY chưa được đặt. "
            "Thêm vào .env: OPENROUTER_API_KEY=your_key"
        )

    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    http_client = _get_http_client()

    http_kwargs: dict = {}
    if http_client is not None:
        http_kwargs["http_client"] = http_client

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        openai_api_key=api_key,
        openai_api_base=_OPENROUTER_BASE,
        default_headers=_DEFAULT_HEADERS,
        request_timeout=45,
        **http_kwargs,
    )


def get_llm_fast(temperature: float = 0) -> ChatOpenAI:
    """LLM với max_tokens nhỏ — dùng cho classify (router)."""
    return get_llm(temperature=temperature, max_tokens=128)


def get_llm_creative(temperature: float = 0.3) -> ChatOpenAI:
    """LLM với temperature cao hơn — dùng cho answer generation."""
    return get_llm(temperature=temperature, max_tokens=400)