"""
backend/app/db.py
─────────────────
Singleton connection tới SQLite database.
Dùng check_same_thread=False vì FastAPI chạy multi-thread.
"""

import sqlite3
from pathlib import Path
from functools import lru_cache

def _find_project_root() -> Path:
    """Tìm PROJECT_ROOT (thư mục chứa cả backend/ và data/)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "backend").exists() and (parent / "data").exists():
            return parent
        if (parent / "backend").exists() and (parent / "scripts").exists():
            return parent
    # Fallback: 3 cấp lên từ backend/app/db.py = project root
    return Path(__file__).resolve().parents[3]

DB_PATH = _find_project_root() / "data" / "university.db"


@lru_cache(maxsize=1)
def get_connection() -> sqlite3.Connection:
    """
    Trả về một connection dùng chung cho toàn bộ app.
    row_factory = sqlite3.Row → truy cập cột bằng tên thay vì index.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database không tồn tại: {DB_PATH}\n"
            "Hãy chạy: python scripts/init_db.py"
        )
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # cải thiện read concurrency
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def execute_query(sql: str, params: tuple = ()) -> list[dict]:
    """
    Thực thi một câu SELECT và trả về list[dict].
    Chỉ cho phép SELECT — ném ValueError nếu gặp lệnh ghi.
    Timeout 5 giây.
    """
    sql_upper = sql.strip().upper()
    forbidden = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "PRAGMA")
    for kw in forbidden:
        if sql_upper.startswith(kw):
            raise ValueError(f"Câu lệnh '{kw}' không được phép — chỉ hỗ trợ SELECT.")

    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.OperationalError as e:
        raise RuntimeError(str(e)) from e


def get_schema_info() -> dict[str, list[str]]:
    """
    Trả về schema của tất cả bảng dạng {table_name: [col_name, ...]}.
    Dùng trong Schema Retrieval Agent.
    """
    conn = get_connection()
    tables_cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row["name"] for row in tables_cur.fetchall()]

    schema: dict[str, list[str]] = {}
    for table in tables:
        cols_cur = conn.execute(f"PRAGMA table_info({table})")
        schema[table] = [row["name"] for row in cols_cur.fetchall()]

    return schema