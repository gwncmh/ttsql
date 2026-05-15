from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.orchestrator import run_text_to_sql_pipeline

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = run_text_to_sql_pipeline(user_question=request.message)
    return ChatResponse(**result)
