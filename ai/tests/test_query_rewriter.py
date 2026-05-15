import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from ai.agents.query_rewriter import rewrite_query


def main() -> None:
    sample = "Bạn có thể đưa ra 3 sinh viên GPA cao nhất năm học 2025-2026"
    rewritten = rewrite_query(sample)
    print("Input:")
    print(sample)
    print("\nOutput:")
    print(rewritten)


if __name__ == "__main__":
    main()
