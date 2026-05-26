"""
backend/app/main.py
────────────────────
FastAPI entry point. Lifespan: kiểm tra DB + warm up LangGraph.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.upload import router as upload_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:4173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Đang khởi động Text-to-SQL backend...")

    # ── 1. Kiểm tra DB ────────────────────────────────────────────────────────
    try:
        from app.db_manager import get_active_connection, get_active_schema  # ← fix tên hàm, fix import path
        get_active_connection()
        schema = get_active_schema()
        logger.info(
            "✓ Database kết nối thành công — %d bảng: %s",
            len(schema), list(schema.keys()),
        )
    except FileNotFoundError as e:
        logger.error("✗ %s", e)
        logger.error("  → Hãy chạy: python scripts/init_db.py")
    except Exception as e:
        logger.error("✗ Lỗi kết nối database: %s", e)

    # ── 2. Warm up LangGraph ──────────────────────────────────────────────────
    try:
        from ai.agents.graph import get_graph
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, get_graph)
        logger.info("✓ LangGraph compiled và sẵn sàng.")
    except Exception as e:
        logger.warning("⚠ LangGraph warm-up thất bại: %s", e)

    yield

    logger.info("Backend đang tắt...")


app = FastAPI(
    title="Text-to-SQL Chatbot API",
    version="0.4.0",
    description="Multi-Agent Text-to-SQL với RAG, Adaptive Routing và Dynamic DB",
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
def health_check() -> dict:
    from app.db_manager import get_active_label  # ← dùng hàm có thật, fix import path
    return {"status": "ok", "version": "0.4.0", "db": get_active_label()}


app.include_router(chat_router, prefix="/api")
app.include_router(upload_router, prefix="/api")  # ← fix: dùng upload_router, thêm prefix