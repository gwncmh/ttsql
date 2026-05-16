"""
backend/app/schemas/chat.py
"""

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Câu hỏi ngôn ngữ tự nhiên từ người dùng",
    )

    @field_validator("message")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Câu hỏi không được để trống.")
        return stripped


class ChatResponse(BaseModel):
    rewritten_query: str        = Field(description="Câu hỏi sau khi được chuẩn hóa")
    complexity:      str        = Field(description="SIMPLE hoặc COMPLEX")
    sql:             str        = Field(description="Câu SQL được sinh ra")
    answer:          str        = Field(description="Câu trả lời ngôn ngữ tự nhiên")
    rows:            list[dict] = Field(default=[], description="Kết quả truy vấn dạng list[dict]")