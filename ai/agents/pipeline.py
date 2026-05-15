from ai.agents.query_rewriter import rewrite_query


def schema_retrieval(_: str) -> dict[str, list[str]]:
    return {
        "tables": ["students", "majors", "faculties"],
        "columns": ["students.name", "students.gpa", "majors.id", "faculties.name"],
    }


def adaptive_router(rewritten_query: str) -> str:
    complex_keywords = ("group by", "having", "subquery", "union", "join")
    lowered = rewritten_query.lower()
    return "COMPLEX" if any(k in lowered for k in complex_keywords) else "SIMPLE"


def sql_generator(_: str, complexity: str, __: dict[str, list[str]]) -> str:
    if complexity == "COMPLEX":
        return (
            "SELECT s.name, AVG(s.gpa) AS avg_gpa "
            "FROM students s GROUP BY s.name ORDER BY avg_gpa DESC LIMIT 5;"
        )
    return "SELECT name, gpa FROM students ORDER BY gpa DESC LIMIT 3;"


def execution_feedback(_: str) -> list[dict[str, str]]:
    return [
        {"name": "Nguyen A", "gpa": "3.95"},
        {"name": "Tran B", "gpa": "3.80"},
        {"name": "Le C", "gpa": "3.75"},
    ]


def answer_generation(user_question: str, rows: list[dict[str, str]]) -> str:
    if not rows:
        return f"Khong tim thay du lieu phu hop voi cau hoi: {user_question}"
    formatted = ", ".join(f"{r['name']} ({r['gpa']})" for r in rows)
    return f"Ket qua cho cau hoi '{user_question}': {formatted}"


def run_pipeline(user_question: str) -> dict[str, str]:
    rewritten_query = rewrite_query(user_question)
    schema = schema_retrieval(rewritten_query)
    complexity = adaptive_router(rewritten_query)
    sql = sql_generator(rewritten_query, complexity, schema)
    rows = execution_feedback(sql)
    answer = answer_generation(user_question, rows)
    return {
        "rewritten_query": rewritten_query,
        "complexity": complexity,
        "sql": sql,
        "answer": answer,
    }
