"""
ai/tests/test_pipeline.py
──────────────────────────
Test end-to-end toàn bộ pipeline với một số câu hỏi mẫu.
Yêu cầu:
  1. python scripts/init_db.py  (tạo DB)
  2. .env có OPENROUTER_API_KEY  (nếu muốn test với LLM thật)
  3. python ai/tests/test_pipeline.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.agents.pipeline import run_pipeline


TEST_QUESTIONS = [
    "Top 3 sinh viên có GPA cao nhất?",
    "Đếm số sinh viên theo từng khoa.",
    "Sinh viên nào có GPA lớn hơn 3.5?",
    "GPA trung bình của từng ngành là bao nhiêu?",
]


def main() -> None:
    print("=" * 70)
    print("TEXT-TO-SQL PIPELINE — END-TO-END TEST")
    print("=" * 70)

    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[Test {i}/{len(TEST_QUESTIONS)}]")
        print(f"  Câu hỏi: {question}")
        print("-" * 50)

        try:
            result = run_pipeline(user_question=question)
            print(f"  Rewritten : {result['rewritten_query']}")
            print(f"  Complexity: {result['complexity']}")
            print(f"  SQL       : {result['sql']}")
            print(f"  Answer    : {result['answer']}")
        except Exception as exc:
            print(f"  ✗ LỖI: {exc}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()