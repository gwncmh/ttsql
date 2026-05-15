from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = None
for parent in CURRENT_FILE.parents:
    if (parent / "ai").exists():
        PROJECT_ROOT = parent
        break

if PROJECT_ROOT is None:
    PROJECT_ROOT = CURRENT_FILE.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from ai.agents.pipeline import run_pipeline  # noqa: E402


def run_text_to_sql_pipeline(user_question: str) -> dict[str, str]:
    return run_pipeline(user_question=user_question)
