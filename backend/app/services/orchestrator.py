"""
backend/app/services/orchestrator.py
──────────────────────────────────────
Cầu nối giữa backend FastAPI và ai.agents.pipeline.
Xử lý sys.path để import hoạt động đúng trong mọi context.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Tìm PROJECT_ROOT (thư mục chứa cả backend/ và ai/)
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT: Path | None = None
for parent in CURRENT_FILE.parents:
    if (parent / "ai").exists() and (parent / "backend").exists():
        PROJECT_ROOT = parent
        break

if PROJECT_ROOT is None:
    PROJECT_ROOT = CURRENT_FILE.parents[3]
    logger.warning("PROJECT_ROOT không tìm thấy tự động — dùng: %s", PROJECT_ROOT)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.agents.pipeline import run_pipeline  # noqa: E402


def run_text_to_sql_pipeline(user_question: str) -> dict[str, str]:
    """
    Entry point cho backend — gọi pipeline AI và trả về kết quả.
    Mọi exception từ pipeline đều được propagate lên để API handler xử lý.
    """
    logger.info("Orchestrator: bắt đầu pipeline cho '%s'", user_question[:80])
    return run_pipeline(user_question=user_question)