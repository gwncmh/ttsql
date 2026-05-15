from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Natural language user query")


class ChatResponse(BaseModel):
    rewritten_query: str
    complexity: str
    sql: str
    answer: str
