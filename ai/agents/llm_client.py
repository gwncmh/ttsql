"""
ai/agents/llm_client.py
────────────────────────
Cấu hình LLM duy nhất cho toàn pipeline.

Dùng langchain_openai.ChatOpenAI trỏ vào OpenRouter.
→ Không còn hard-code httpx calls rải rác trong từng agent.
→ Retry / timeout / SSL handle bởi LangChain + httpx bên dưới.

Usage:
    from ai.agents.llm_client import get_llm, get_llm_fast

    llm = get_llm()                       # model mặc định, temperature=0
    llm_creative = get_llm(temperature=0.3)
    llm_fast = get_llm_fast()             # max_tokens nhỏ hơn cho classify
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
    """Trả về cấu hình TLS verify, giống logic cũ."""
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


def get_llm(
    temperature: float = 0,
    max_tokens: int = 512,
) -> ChatOpenAI:
    """
    Trả về ChatOpenAI instance kết nối OpenRouter.
    LangChain tự xử lý retry (với with_retry) và streaming.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY chưa được đặt. "
            "Thêm vào .env: OPENROUTER_API_KEY=your_key"
        )

    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    verify = _get_verify()

    # http_client_kwargs cho httpx bên dưới LangChain
    http_kwargs: dict = {}
    if verify is False:
        import httpx
        http_kwargs["http_client"] = httpx.Client(verify=False)
    elif isinstance(verify, str):
        import httpx
        import ssl as _ssl
        ctx = _ssl.create_default_context(cafile=verify)
        http_kwargs["http_client"] = httpx.Client(ssl_context=ctx)

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
    return get_llm(temperature=temperature, max_tokens=20)


def get_llm_creative(temperature: float = 0.3) -> ChatOpenAI:
    """LLM với temperature cao hơn — dùng cho answer generation."""
    return get_llm(temperature=temperature, max_tokens=400)