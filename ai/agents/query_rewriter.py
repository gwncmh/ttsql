import os
import warnings

import certifi
import httpx
from dotenv import load_dotenv

load_dotenv()

REWRITE_PROMPT = "Rewrite the user query clearly for SQL generation."
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


def _ssl_verify_arg():
    """
    Pick TLS verify bundle for httpx.

    Default: certifi CA bundle (fixes many Windows/Python setups).

    Override with SSL_CERT_FILE or REQUESTS_CA_BUNDLE (path to .pem) when
    behind a corporate proxy / custom root CA.

    Dev-only escape hatch: OPENROUTER_SSL_VERIFY=0|false disables verification
    (insecure; do not use in production).
    """
    flag = os.getenv("OPENROUTER_SSL_VERIFY", "true").strip().lower()
    if flag in ("0", "false", "no", "off"):
        warnings.warn(
            "TLS verification is disabled (OPENROUTER_SSL_VERIFY). "
            "Use only for local debugging.",
            stacklevel=2,
        )
        return False

    for key in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        path = os.getenv(key)
        if path and os.path.isfile(path):
            return path

    return certifi.where()


def rewrite_query(user_query: str) -> str:
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is missing.")

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": REWRITE_PROMPT},
            {"role": "user", "content": user_query},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "TextToSQL"
    }

    with httpx.Client(timeout=60.0, verify=_ssl_verify_arg()) as client:
        response = client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()
