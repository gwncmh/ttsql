"""
backend/app/api/chat.py
────────────────────────
POST /api/chat endpoint.
Pipeline chạy đồng bộ (blocking I/O với LLM) →
dùng run_in_executor để không block event loop FastAPI.
"""

import asyncio
import logging
from functools import partial

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.orchestrator import run_text_to_sql_pipeline

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Nhận câu hỏi → chạy pipeline → trả kết quả.
    Async để không block event loop khi pipeline gọi LLM (blocking HTTP).
    """
    logger.info("POST /api/chat — message: %s", request.message[:80])

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None,
            partial(run_text_to_sql_pipeline, user_question=request.message),
        )
    except Exception as exc:
        logger.error("Pipeline thất bại: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi pipeline: {exc}",
        )

    return ChatResponse(**result)