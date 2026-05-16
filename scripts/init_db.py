"""
scripts/init_db.py
──────────────────
Tạo SQLite database với dữ liệu mẫu: faculties, majors, students, scores.
Chạy một lần trước khi khởi động backend:
    python scripts/init_db.py
"""

import sqlite3
import random
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "university.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

FACULTIES = [
    (1, "Công nghệ thông tin"),
    (2, "Kinh tế"),
    (3, "Kỹ thuật"),
    (4, "Ngoại ngữ"),
]

MAJORS = [
    (1, "Khoa học máy tính", 1),
    (2, "Kỹ thuật phần mềm", 1),
    (3, "An toàn thông tin", 1),
    (4, "Kế toán", 2),
    (5, "Quản trị kinh doanh", 2),
    (6, "Cơ điện tử", 3),
    (7, "Kỹ thuật điện", 3),
    (8, "Tiếng Anh", 4),
    (9, "Tiếng Nhật", 4),
]

STUDENT_NAMES = [
    "Nguyễn Văn An", "Trần Thị Bình", "Lê Minh Cường", "Phạm Thị Dung",
    "Hoàng Văn Em", "Vũ Thị Fương", "Đặng Văn Giang", "Bùi Thị Hoa",
    "Ngô Văn Inh", "Đinh Thị Kim", "Lý Văn Long", "Mai Thị Minh",
    "Tô Văn Nam", "Lê Thị Oanh", "Trịnh Văn Phong", "Cao Thị Quỳnh",
    "Dương Văn Rồng", "Hồ Thị Sen", "Phan Văn Tuấn", "Chu Thị Uyên",
    "Trương Văn Việt", "Võ Thị Xuân", "Lưu Văn Yên", "Đỗ Thị Zung",
    "Nguyễn Thị Ánh", "Trần Văn Bảo", "Lê Thị Chi", "Phạm Văn Dũng",
]

SUBJECTS = [
    "Toán cao cấp", "Lập trình Python", "Cơ sở dữ liệu",
    "Mạng máy tính", "Trí tuệ nhân tạo", "Kỹ thuật phần mềm",
    "Kinh tế vi mô", "Kế toán tài chính", "Tiếng Anh chuyên ngành",
]

random.seed(42)


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Đã xóa DB cũ: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── Schema ────────────────────────────────────────────────────────────────
    cur.executescript("""
        CREATE TABLE faculties (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE majors (
            id         INTEGER PRIMARY KEY,
            name       TEXT NOT NULL UNIQUE,
            faculty_id INTEGER NOT NULL REFERENCES faculties(id)
        );

        CREATE TABLE students (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            gpa      REAL NOT NULL CHECK (gpa >= 0 AND gpa <= 4),
            major_id INTEGER NOT NULL REFERENCES majors(id),
            year     INTEGER NOT NULL CHECK (year BETWEEN 1 AND 6)
        );

        CREATE TABLE scores (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id),
            subject    TEXT NOT NULL,
            score      REAL NOT NULL CHECK (score >= 0 AND score <= 10)
        );

        CREATE INDEX idx_students_gpa      ON students(gpa DESC);
        CREATE INDEX idx_students_major_id ON students(major_id);
        CREATE INDEX idx_scores_student_id ON scores(student_id);
    """)

    # ── Dữ liệu ───────────────────────────────────────────────────────────────
    cur.executemany("INSERT INTO faculties VALUES (?, ?)", FACULTIES)
    cur.executemany("INSERT INTO majors VALUES (?, ?, ?)", MAJORS)

    students = []
    for i, name in enumerate(STUDENT_NAMES, start=1):
        major_id = random.choice([m[0] for m in MAJORS])
        gpa      = round(random.uniform(2.0, 4.0), 2)
        year     = random.randint(1, 4)
        students.append((name, gpa, major_id, year))

    cur.executemany(
        "INSERT INTO students (name, gpa, major_id, year) VALUES (?, ?, ?, ?)",
        students,
    )

    # Mỗi sinh viên có 3-5 điểm môn học ngẫu nhiên
    scores = []
    for sid in range(1, len(students) + 1):
        num_subjects = random.randint(3, 5)
        for subj in random.sample(SUBJECTS, num_subjects):
            scores.append((sid, subj, round(random.uniform(4.0, 10.0), 1)))

    cur.executemany(
        "INSERT INTO scores (student_id, subject, score) VALUES (?, ?, ?)",
        scores,
    )

    conn.commit()
    conn.close()

    print(f"✓ Database tạo thành công: {DB_PATH}")
    print(f"  - {len(FACULTIES)} khoa")
    print(f"  - {len(MAJORS)} ngành")
    print(f"  - {len(students)} sinh viên")
    print(f"  - {len(scores)} điểm số")


if __name__ == "__main__":
    main()