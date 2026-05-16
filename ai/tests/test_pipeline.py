"""
ai/tests/test_pipeline.py
──────────────────────────
Test end-to-end pipeline với LangGraph.

Cách chạy:
  1. python scripts/init_db.py          (tạo DB lần đầu)
  2. Đặt OPENROUTER_API_KEY trong .env
  3. python ai/tests/test_pipeline.py

Có thể stream từng bước với graph.stream() để debug.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.agents.pipeline import run_pipeline
from ai.agents.graph import get_graph

TEST_QUESTIONS = [
    "Top 3 sinh viên có GPA cao nhất?",
    "Đếm số sinh viên theo từng khoa.",
    "Sinh viên nào có GPA lớn hơn 3.5?",
    "GPA trung bình của từng ngành là bao nhiêu?",
    "Khoa nào có nhiều sinh viên nhất?",
]


def test_full_pipeline():
    """Test invoke bình thường."""
    print("=" * 70)
    print("TEXT-TO-SQL — LANGGRAPH PIPELINE TEST")
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


def test_stream_single():
    """
    Demo: stream từng bước LangGraph để debug.
    Mỗi node hoàn thành sẽ in ra state thay đổi.
    """
    print("\n" + "=" * 70)
    print("STREAM MODE — xem từng node")
    print("=" * 70)

    graph = get_graph()
    question = "GPA trung bình của từng ngành là bao nhiêu?"
    print(f"Câu hỏi: {question}\n")

    for step in graph.stream({"user_question": question}):
        node_name = list(step.keys())[0]
        node_output = step[node_name]
        print(f"[{node_name}]")
        for k, v in node_output.items():
            val_str = str(v)[:120] + ("..." if len(str(v)) > 120 else "")
            print(f"  {k}: {val_str}")
        print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream", action="store_true",
                        help="Chạy stream mode thay vì full pipeline test")
    args = parser.parse_args()

    if args.stream:
        test_stream_single()
    else:
        test_full_pipeline()