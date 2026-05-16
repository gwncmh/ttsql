"""
ai/agents/schema_retrieval.py
──────────────────────────────
Agent 2: Truy xuất schema liên quan từ SQLite database.

Chiến lược:
1. Đọc toàn bộ schema qua PRAGMA table_info
2. Dùng keyword matching để lọc bảng liên quan đến câu hỏi
3. Luôn trả về ít nhất bảng "students" (core entity)
4. Trả về foreign key relations để SQL Generator dùng khi JOIN
"""

import re
import logging
import sys
from pathlib import Path

# Đảm bảo import db module hoạt động dù chạy từ bất kỳ đâu
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db import get_schema_info  # noqa: E402

logger = logging.getLogger(__name__)

# Map từ khóa trong câu hỏi → tên bảng liên quan
KEYWORD_TABLE_MAP: dict[str, list[str]] = {
    "sinh viên": ["students"],
    "student":   ["students"],
    "gpa":       ["students"],
    "điểm":      ["scores", "students"],
    "score":     ["scores"],
    "môn":       ["scores"],
    "subject":   ["scores"],
    "khoa":      ["faculties", "majors", "students"],
    "faculty":   ["faculties"],
    "ngành":     ["majors", "students"],
    "major":     ["majors"],
    "năm":       ["students"],
    "year":      ["students"],
}

# Foreign key relations (tĩnh — phù hợp với schema init_db.py)
FK_RELATIONS = [
    ("students.major_id", "majors.id"),
    ("majors.faculty_id", "faculties.id"),
    ("scores.student_id", "students.id"),
]


def retrieve_schema(rewritten_query: str) -> dict:
    """
    Trả về:
    {
        "tables":    {"students": ["id","name","gpa",...], ...},
        "relations": [("students.major_id","majors.id"), ...],
        "full_schema": { ...tất cả bảng... }
    }
    """
    try:
        full_schema = get_schema_info()
    except Exception as exc:
        logger.error("Không đọc được schema: %s", exc)
        return {"tables": {}, "relations": [], "full_schema": {}}

    query_lower = rewritten_query.lower()

    # Tìm bảng liên quan qua keyword matching
    relevant_tables: set[str] = set()
    for keyword, tables in KEYWORD_TABLE_MAP.items():
        if re.search(re.escape(keyword), query_lower):
            for t in tables:
                if t in full_schema:
                    relevant_tables.add(t)

    # Luôn thêm "students" — core entity
    if "students" in full_schema:
        relevant_tables.add("students")

    # Nếu có students → thêm majors và faculties để JOIN đầy đủ
    if "students" in relevant_tables:
        for t in ("majors", "faculties"):
            if t in full_schema:
                relevant_tables.add(t)

    # Nếu có scores → thêm students
    if "scores" in relevant_tables and "students" in full_schema:
        relevant_tables.add("students")

    selected_tables = {t: full_schema[t] for t in sorted(relevant_tables)}

    # Lọc FK chỉ giữ những cái liên quan
    relevant_fk = [
        (src, dst)
        for src, dst in FK_RELATIONS
        if src.split(".")[0] in relevant_tables and dst.split(".")[0] in relevant_tables
    ]

    logger.debug(
        "Schema retrieval: %s table(s) selected: %s",
        len(selected_tables),
        list(selected_tables.keys()),
    )

    return {
        "tables":      selected_tables,
        "relations":   relevant_fk,
        "full_schema": full_schema,
    }


def format_schema_for_prompt(schema_info: dict) -> str:
    """
    Chuyển schema dict thành chuỗi text để đưa vào LLM prompt.
    Ví dụ output:
        Table: students (id, name, gpa, major_id, year)
        Table: majors   (id, name, faculty_id)
        FK: students.major_id → majors.id
    """
    lines = []
    for table, cols in schema_info["tables"].items():
        lines.append(f"Table: {table} ({', '.join(cols)})")
    for src, dst in schema_info["relations"]:
        lines.append(f"FK: {src} → {dst}")
    return "\n".join(lines)