"""
backend/app/api/upload.py
POST /api/upload-db  — nhận file .sqlite/.db, lưu vào /tmp/uploads/, switch active DB.
GET  /api/db-info    — trả về tên DB và schema đang active.
POST /api/reset-db   — về lại DB mặc định.
"""
import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.db_manager import (
    set_active_db, reset_to_default,
    get_active_label, get_active_schema, get_active_fk_relations,
)

router = APIRouter(tags=["database"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(tempfile.gettempdir()) / "text2sql_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload-db")
async def upload_database(file: UploadFile = File(...)) -> JSONResponse:
    """Nhận file SQLite, validate và switch active DB."""
    # Kiểm tra extension
    name = file.filename or "upload.db"
    suffix = Path(name).suffix.lower()
    if suffix not in (".sqlite", ".sqlite3", ".db"):
        raise HTTPException(
            status_code=400,
            detail="Chỉ chấp nhận file .sqlite, .sqlite3, hoặc .db",
        )

    # Đọc nội dung
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File quá lớn (tối đa {MAX_FILE_SIZE // 1024 // 1024} MB).",
        )

    # Lưu vào /tmp
    dest = UPLOAD_DIR / name
    dest.write_bytes(content)

    try:
        set_active_db(dest, label=name)
    except ValueError as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Lỗi khi nạp DB: {e}")

    # Đọc schema của DB mới
    try:
        schema = get_active_schema()
        fk_rels = get_active_fk_relations()
    except Exception as e:
        logger.warning("Không đọc được schema sau upload: %s", e)
        schema = {}
        fk_rels = []

    logger.info("✓ Đã switch sang DB: %s (%d bảng)", name, len(schema))
    return JSONResponse({
        "success": True,
        "db_label": name,
        "tables": {t: cols for t, cols in schema.items()},
        "relations": [{"from": s, "to": d} for s, d in fk_rels],
        "message": f"Đã nạp database '{name}' với {len(schema)} bảng.",
    })


@router.get("/db-info")
def db_info() -> JSONResponse:
    """Trả về thông tin DB đang active."""
    try:
        schema = get_active_schema()
        fk_rels = get_active_fk_relations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse({
        "db_label": get_active_label(),
        "tables": {t: cols for t, cols in schema.items()},
        "relations": [{"from": s, "to": d} for s, d in fk_rels],
    })


@router.post("/reset-db")
def reset_database() -> JSONResponse:
    """Về lại university.db mặc định."""
    try:
        reset_to_default()
        schema = get_active_schema()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse({
        "success": True,
        "db_label": get_active_label(),
        "tables": {t: cols for t, cols in schema.items()},
        "message": "Đã reset về database mặc định.",
    })