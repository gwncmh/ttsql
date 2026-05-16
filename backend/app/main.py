"""
backend/app/main.py
────────────────────
FastAPI application entry point.
- Lifespan hook: kiểm tra DB khi khởi động
- CORS giới hạn origin (không dùng wildcard "*" cho production)
- Health check endpoint
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Origins được phép gọi API — thêm domain production vào đây
ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite dev
    "http://localhost:4173",   # Vite preview
    "http://localhost:3000",   # CRA / Next.js dev (backup)
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Chạy khi app khởi động / tắt."""
    logger.info("Đang khởi động Text-to-SQL backend...")
    try:
        from app.db import get_connection, get_schema_info
        conn = get_connection()
        schema = get_schema_info()
        logger.info(
            "✓ Database kết nối thành công — %d bảng: %s",
            len(schema), list(schema.keys()),
        )
    except FileNotFoundError as e:
        logger.error("✗ %s", e)
        logger.error("  → Hãy chạy: python scripts/init_db.py")
    except Exception as e:
        logger.error("✗ Lỗi kết nối database: %s", e)

    yield   # app đang chạy

    logger.info("Backend đang tắt...")


app = FastAPI(
    title="Text-to-SQL Chatbot API",
    version="0.2.0",
    description="Multi-Agent Text-to-SQL với RAG và Adaptive Routing",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Kiểm tra trạng thái backend."""
    return {"status": "ok", "version": "0.2.0"}


app.include_router(chat_router, prefix="/api")