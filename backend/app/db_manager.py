"""
backend/app/db_manager.py
──────────────────────────
Singleton quản lý DB động. Toàn bộ app (backend + AI pipeline) đều
import module này — Python đảm bảo chỉ load một lần, nên _active_db_path
là shared state thực sự.
"""
import logging
import sqlite3
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Default DB path ───────────────────────────────────────────────────────────
def _default_db_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "university.db"
        if candidate.exists():
            return candidate
    # Fallback nếu chưa có DB (chưa chạy init_db.py)
    return Path(__file__).resolve().parents[2] / "data" / "university.db"


# ── Module-level state ────────────────────────────────────────────────────────
_lock = threading.Lock()
_active_db_path: Path = _default_db_path()
_active_db_label: str = "university.db (mặc định)"
_connection_cache: dict[str, sqlite3.Connection] = {}


# ── Getters ───────────────────────────────────────────────────────────────────
def get_active_path() -> Path:
    with _lock:
        return _active_db_path


def get_active_label() -> str:
    with _lock:
        return _active_db_label


# ── Switch DB ─────────────────────────────────────────────────────────────────
def set_active_db(path, label: str | None = None) -> None:
    """
    Switch sang DB mới.
    - Validate SQLite magic bytes
    - Đóng và xóa TOÀN BỘ connection cache (không chỉ key cũ)
    - Reset LangGraph singleton
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File không tồn tại: {path}")

    with open(path, "rb") as f:
        header = f.read(16)
    if not header.startswith(b"SQLite format 3"):
        raise ValueError("File không phải SQLite database hợp lệ.")

    with _lock:
        global _active_db_path, _active_db_label, _connection_cache

        # Đóng toàn bộ connection cũ
        for conn in _connection_cache.values():
            try:
                conn.close()
            except Exception:
                pass
        _connection_cache.clear()

        _active_db_path = path
        _active_db_label = label or path.name

    logger.info("[db_manager] Switched → %s | path: %s", _active_db_label, _active_db_path)
    _reset_pipeline_cache()


def reset_to_default() -> None:
    set_active_db(_default_db_path(), "university.db (mặc định)")


# ── Connection ────────────────────────────────────────────────────────────────
def get_active_connection() -> sqlite3.Connection:
    with _lock:
        path_key = str(_active_db_path)
        if path_key not in _connection_cache:
            if not _active_db_path.exists():
                raise FileNotFoundError(
                    f"Database không tồn tại: {_active_db_path}\n"
                    "Hãy chạy: python scripts/init_db.py"
                )
            conn = sqlite3.connect(str(_active_db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            _connection_cache[path_key] = conn
            logger.info("[db_manager] Mở connection mới: %s", path_key)
        return _connection_cache[path_key]


# ── Query ─────────────────────────────────────────────────────────────────────
def execute_query_on_active(sql: str, params: tuple = ()) -> list[dict]:
    sql_upper = sql.strip().upper()
    forbidden = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "PRAGMA")
    for kw in forbidden:
        if sql_upper.startswith(kw):
            raise ValueError(f"Câu lệnh '{kw}' không được phép — chỉ hỗ trợ SELECT.")
    conn = get_active_connection()
    try:
        cur = conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    except sqlite3.OperationalError as e:
        raise RuntimeError(str(e)) from e


# ── Schema ────────────────────────────────────────────────────────────────────
def get_active_schema() -> dict[str, list[str]]:
    conn = get_active_connection()
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    schema = {
        t: [r["name"] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()]
        for t in tables
    }
    logger.debug("[db_manager] get_active_schema() → %d bảng: %s", len(schema), list(schema.keys()))
    return schema


def get_active_fk_relations() -> list[tuple[str, str]]:
    conn = get_active_connection()
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    relations = []
    for table in tables:
        for row in conn.execute(f"PRAGMA foreign_key_list({table})").fetchall():
            to_col = row["to"] or "id"
            relations.append((f"{table}.{row['from']}", f"{row['table']}.{to_col}"))
    return relations


# ── Reset pipeline cache ──────────────────────────────────────────────────────
def _reset_pipeline_cache() -> None:
    """
    Reset LangGraph singleton để graph được compile lại với DB mới.
    Dùng importlib để tránh circular import và đảm bảo nhận đúng module object.
    """
    import importlib
    import sys

    # Reset LangGraph graph singleton
    graph_mod_name = "ai.agents.graph"
    if graph_mod_name in sys.modules:
        try:
            sys.modules[graph_mod_name]._graph_instance = None
            logger.info("[db_manager] Reset LangGraph singleton.")
        except Exception as e:
            logger.warning("[db_manager] Không reset được LangGraph: %s", e)

    # Reset lru_cache của db.py nếu có
    db_mod_name = "backend.app.db"
    if db_mod_name in sys.modules:
        try:
            sys.modules[db_mod_name].get_connection.cache_clear()
            logger.info("[db_manager] Cleared db.py connection cache.")
        except Exception as e:
            logger.warning("[db_manager] Không clear được db.py cache: %s", e)